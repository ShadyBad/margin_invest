"use client"

import { signIn } from "next-auth/react"

const providers = [
  { id: "google", name: "Google" },
  { id: "microsoft-entra-id", name: "Microsoft" },
  { id: "facebook", name: "Facebook" },
  { id: "github", name: "GitHub" },
]

export function LoginButtons() {
  return (
    <div className="flex flex-col gap-3 w-full max-w-sm">
      {providers.map((provider) => (
        <button
          key={provider.id}
          onClick={() => signIn(provider.id, { callbackUrl: "/dashboard" })}
          className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors"
        >
          Sign in with {provider.name}
        </button>
      ))}
    </div>
  )
}
