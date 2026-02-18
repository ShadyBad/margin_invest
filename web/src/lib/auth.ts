import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import Credentials from "next-auth/providers/credentials"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

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
      },
      async authorize(credentials) {
        const res = await fetch(`${API_URL}/api/v1/auth/verify-credentials`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: credentials.username,
            password: credentials.password,
          }),
        })

        if (!res.ok) return null

        const data = await res.json()

        return {
          id: data.userId,
          name: data.name,
          email: data.email,
          mfaStatus: data.mfaStatus,
          challengeToken: data.challengeToken,
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

      if (mfaStatus === "not_configured") {
        return `/mfa/setup?userId=${user.id}`
      }

      if (mfaStatus === "configured" && !mfaToken) {
        return `/mfa/verify?userId=${user.id}`
      }

      return true
    },
    async jwt({ token, user, account }) {
      if (user) {
        token.userId = user.id
        token.authMethod = account?.type === "oauth" || account?.type === "oidc"
          ? "oauth"
          : "credentials"
        token.oauthProvider = token.authMethod === "oauth"
          ? (account?.provider ?? null)
          : null
        token.mfaVerified = token.authMethod === "oauth"
          ? true
          : !!(user as Record<string, unknown>).mfaToken

        // Avatar: OAuth providers include image in user profile
        if (token.authMethod === "oauth" && user.image) {
          token.oauthAvatarUrl = user.image
        }
        // Avatar: credentials provider returns avatar_url from API
        const avatarUrl = (user as Record<string, unknown>).avatarUrl as string | undefined
        if (avatarUrl) {
          token.avatarUrl = avatarUrl
        }
      } else if (token.authMethod === "credentials" && token.userId) {
        // Token refresh for credentials users — check if password was changed.
        // Throttled to every 60 seconds to avoid excessive API calls.
        const now = Math.floor(Date.now() / 1000)
        const lastCheck = (token.sessionCheckAt as number) || 0

        if (now - lastCheck > 60) {
          try {
            const res = await fetch(
              `${API_URL}/api/v1/auth/session-check/${token.userId}`
            )
            if (res.ok) {
              const data = await res.json()
              if (data.password_changed_at) {
                const changedAt = Math.floor(
                  new Date(data.password_changed_at).getTime() / 1000
                )
                const tokenIat = (token.iat as number) || 0
                if (changedAt > tokenIat) {
                  // Password was changed after this token was issued — invalidate
                  return {} as typeof token
                }
              }
            }
            token.sessionCheckAt = now
          } catch {
            // If API is unavailable, don't invalidate — just skip the check
            token.sessionCheckAt = now
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
      session.avatarUrl = (token.avatarUrl as string) || null
      session.oauthAvatarUrl = (token.oauthAvatarUrl as string) || null
      return session
    },
  },
})
