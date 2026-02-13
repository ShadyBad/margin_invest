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
    jwt({ token, user, account }) {
      if (user) {
        token.userId = user.id
        token.authMethod = account?.type === "oauth" || account?.type === "oidc"
          ? "oauth"
          : "credentials"
        token.mfaVerified = token.authMethod === "oauth"
          ? true
          : !!(user as Record<string, unknown>).mfaToken
      }
      return token
    },
    session({ session, token }) {
      session.userId = token.userId as string
      session.authMethod = token.authMethod as string
      session.mfaVerified = token.mfaVerified as boolean
      return session
    },
  },
})
