"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import Link from "next/link"

const oauthProviders = [
  { id: "google", name: "Google" },
  { id: "github", name: "GitHub" },
]

export function LoginButtons() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    signIn("credentials", {
      username,
      password,
      callbackUrl: "/dashboard",
    })
  }

  return (
    <div className="flex flex-col gap-3 w-full max-w-sm">
      {oauthProviders.map((provider) => (
        <button
          key={provider.id}
          onClick={() => signIn(provider.id, { callbackUrl: "/dashboard" })}
          className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors"
        >
          Sign in with {provider.name}
        </button>
      ))}

      <div className="flex items-center gap-3 my-2">
        <div className="flex-1 h-px bg-[#1E2740]" />
        <span className="text-sm text-[#8A8473]">or continue with</span>
        <div className="flex-1 h-px bg-[#1E2740]" />
      </div>

      <form onSubmit={handleCredentialsSubmit} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="username" className="text-sm text-[#8A8473]">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors"
            placeholder="Enter your username"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-sm text-[#8A8473]">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors"
            placeholder="Enter your password"
          />
        </div>

        <button
          type="submit"
          className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
        >
          Sign In
        </button>
      </form>

      <p className="text-sm text-[#8A8473] text-center mt-2">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-[#D4A843] hover:underline">
          Create one
        </Link>
      </p>
    </div>
  )
}
