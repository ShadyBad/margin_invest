import NextAuth, { CredentialsSignin } from "next-auth"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import Credentials from "next-auth/providers/credentials"

// Server-side only — NextAuth runs on the server, needs full URL for direct API calls
const API_URL = process.env.API_URL || "http://localhost:8000"

class InvalidCredentialsError extends CredentialsSignin {
  code = "invalid_credentials"
}

class AccountLockedError extends CredentialsSignin {
  code = "account_locked"
}

class ApiUnreachableError extends CredentialsSignin {
  code = "api_unreachable"
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
    Credentials({
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
        mfaToken: { label: "MFA Token", type: "text" },
        mfaCompletionToken: { label: "MFA Completion Token", type: "text" },
      },
      async authorize(credentials) {
        // Path 1: MFA completion token (no password needed)
        if (credentials.mfaCompletionToken) {
          let verifyRes: Response
          try {
            verifyRes = await fetch(`${API_URL}/api/v1/auth/verify-mfa-token`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: credentials.mfaCompletionToken }),
            })
          } catch (error) {
            console.error("[auth] Failed to verify MFA token", error)
            throw new ApiUnreachableError()
          }

          if (!verifyRes.ok) {
            throw new InvalidCredentialsError()
          }

          const userData = await verifyRes.json()
          return {
            id: String(userData.id),
            name: userData.username,
            email: userData.email,
            mfaStatus: "enabled",
            mfaToken: "verified",
            avatarUrl: userData.avatar_url,
          }
        }

        // Path 2: Existing username/password flow
        let res: Response
        try {
          res = await fetch(`${API_URL}/api/v1/auth/verify-credentials`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          })
        } catch (error) {
          console.error("[auth] Failed to reach API at", API_URL, error)
          throw new ApiUnreachableError()
        }

        if (!res.ok) {
          if (res.status === 423 || res.status === 429) {
            throw new AccountLockedError()
          }
          throw new InvalidCredentialsError()
        }

        const data = await res.json()

        return {
          id: String(data.id),
          name: data.username,
          email: data.email,
          mfaStatus: data.mfa_status,
          challengeToken: data.challenge_token,
          mfaToken: credentials.mfaToken as string | undefined,
          avatarUrl: data.avatar_url,
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
    error: "/auth/error",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    signIn({ user, account }) {
      // OAuth providers: allow immediately
      if (account?.type === "oauth" || account?.type === "oidc") {
        return true
      }

      // Credentials provider: check MFA status
      const mfaStatus = (user as Record<string, unknown>).mfaStatus as string | undefined
      const mfaToken = (user as Record<string, unknown>).mfaToken as string | undefined
      const challengeToken = (user as Record<string, unknown>).challengeToken as string | undefined

      if (mfaStatus === "disabled") {
        return `/api/mfa-redirect?userId=${user.id}&challengeToken=${challengeToken}&setup=true`
      }

      if (mfaStatus === "enabled" && !mfaToken) {
        return `/api/mfa-redirect?userId=${user.id}&challengeToken=${challengeToken}&setup=false`
      }

      return true
    },
    async jwt({ token, user, account }) {
      if (user) {
        token.authMethod = account?.type === "oauth" || account?.type === "oidc"
          ? "oauth"
          : "credentials"
        token.oauthProvider = token.authMethod === "oauth"
          ? (account?.provider ?? null)
          : null
        token.mfaVerified = token.authMethod === "oauth"
          ? true
          : !!(user as Record<string, unknown>).mfaToken

        // OAuth: sync user to backend and get database ID
        if (token.authMethod === "oauth" && account) {
          try {
            const syncRes = await fetch(`${API_URL}/api/v1/auth/oauth-sync`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                email: user.email,
                name: user.name,
                provider: account.provider,
                oauth_id: account.providerAccountId,
                avatar_url: user.image,
              }),
            })
            if (syncRes.ok) {
              const syncData = await syncRes.json()
              token.userId = String(syncData.id)
            } else {
              // Fallback to provider ID if sync fails
              token.userId = user.id
            }
          } catch {
            // If API is unavailable, fall back to provider ID
            token.userId = user.id
          }
        } else {
          token.userId = user.id
        }

        // Avatar: OAuth providers include image in user profile
        if (token.authMethod === "oauth" && user.image) {
          token.oauthAvatarUrl = user.image
        }
        // Avatar: credentials provider returns avatar_url from API
        const avatarUrl = (user as Record<string, unknown>).avatarUrl as string | undefined
        if (avatarUrl) {
          token.avatarUrl = avatarUrl
        }

        // Fetch security status for the user (both OAuth and credentials)
        if (token.userId) {
          try {
            const securityRes = await fetch(`${API_URL}/api/v1/auth/security-status`, {
              headers: { "X-User-Id": String(token.userId) },
            })
            if (securityRes.ok) {
              const security = await securityRes.json()
              token.hasPassword = security.has_password
              token.mfaEnabled = security.mfa_enabled
              token.mfaGraceDeadline = security.mfa_grace_deadline ?? null
              token.linkedProviders = (security.linked_providers ?? []).map(
                (lp: { provider: string }) => lp.provider
              )
            }
          } catch {
            // If API is unavailable, leave security fields unset
          }
        }
      } else if (token.userId) {
        // Token refresh for ALL users — throttled to every 60 seconds.
        const now = Math.floor(Date.now() / 1000)
        const lastCheck = (token.sessionCheckAt as number) || 0

        if (now - lastCheck > 60) {
          // Credentials-only: check if password was changed
          if (token.authMethod === "credentials") {
            try {
              const res = await fetch(
                `${API_URL}/api/v1/auth/session-check/${token.userId}?iat=${token.iat || 0}`
              )
              if (res.ok) {
                const data = await res.json()
                if (data.token_invalidated) {
                  return {} as typeof token
                }
              }
            } catch {
              // If API is unavailable, don't invalidate — just skip the check
            }
          }

          token.sessionCheckAt = now

          // All users: refresh security status
          try {
            const securityRes = await fetch(`${API_URL}/api/v1/auth/security-status`, {
              headers: { "X-User-Id": String(token.userId) },
            })
            if (securityRes.ok) {
              const security = await securityRes.json()
              token.hasPassword = security.has_password
              token.mfaEnabled = security.mfa_enabled
              token.mfaGraceDeadline = security.mfa_grace_deadline ?? null
              token.linkedProviders = (security.linked_providers ?? []).map(
                (lp: { provider: string }) => lp.provider
              )
            }
          } catch {
            // If API is unavailable, keep stale security info
          }
        }
      }
      return token
    },
    session({ session, token }) {
      session.userId = token.userId as string
      session.authMethod = token.authMethod as string
      session.oauthProvider = (token.oauthProvider as string) || null
      session.mfaVerified = token.mfaVerified as boolean
      session.hasPassword = (token.hasPassword as boolean) ?? false
      session.mfaEnabled = (token.mfaEnabled as boolean) ?? false
      session.mfaGraceDeadline = (token.mfaGraceDeadline as string) ?? null
      session.linkedProviders = (token.linkedProviders as string[]) ?? []
      session.avatarUrl = (token.avatarUrl as string) || null
      session.oauthAvatarUrl = (token.oauthAvatarUrl as string) || null
      return session
    },
  },
})
