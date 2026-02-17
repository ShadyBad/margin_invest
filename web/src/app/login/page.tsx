import type { Metadata } from "next"
import { LoginScene } from "@/components/login/login-scene"
import { LoginCard } from "@/components/login/login-card"

export const metadata: Metadata = {
  title: "Sign In | Margin Invest",
  description: "Sign in to your Margin Invest account.",
}

export default function LoginPage() {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <LoginScene />
      <div className="relative z-10">
        <LoginCard />
      </div>
    </div>
  )
}
