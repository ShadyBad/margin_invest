import "next-auth"
import "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    userId: string
    authMethod: string
    oauthProvider: string | null
    mfaVerified: boolean
    hasPassword: boolean
    mfaEnabled: boolean
    mfaGraceDeadline: string | null
    linkedProviders: string[]
    avatarUrl: string | null
    oauthAvatarUrl: string | null
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId?: string
    authMethod?: string
    oauthProvider?: string | null
    mfaVerified?: boolean
    hasPassword?: boolean
    mfaEnabled?: boolean
    mfaGraceDeadline?: string | null
    linkedProviders?: string[]
    avatarUrl?: string | null
    oauthAvatarUrl?: string | null
  }
}
