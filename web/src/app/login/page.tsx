import type { Metadata } from "next"
import { LoginScene } from "@/components/login/login-scene"
import { LoginCard } from "@/components/login/login-card"

export const metadata: Metadata = {
  title: "Sign In | Margin Invest",
  description: "Sign in to your Margin Invest account.",
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string; error?: string; code?: string; resetSuccess?: string }>
}) {
  const params = await searchParams
  const initialMode = params.mode === "signup" ? "signup" : "signin"

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <LoginScene />
      <div className="relative z-10">
        <LoginCard
          initialMode={initialMode}
          authError={params.error}
          authCode={params.code}
          resetSuccess={params.resetSuccess === "true"}
        />
      </div>
    </div>
  )
}
