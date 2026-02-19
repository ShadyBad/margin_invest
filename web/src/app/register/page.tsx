"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"

// Use relative URL — Vercel rewrite (vercel.json) and Next.js rewrite
// (next.config.ts) both proxy /api/v1/* to the backend, avoiding CORS.

export default function RegisterPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      const res = await fetch(`/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || "Registration failed")
        return
      }

      router.push("/login")
    } catch {
      setError("An unexpected error occurred")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-sm">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">
          Create an Account
        </h1>

        {error && (
          <p className="text-red-400 text-sm w-full text-center">{error}</p>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full">
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
              required
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="email" className="text-sm text-[#8A8473]">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors"
              placeholder="Enter your email"
              required
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
              minLength={12}
              required
            />
          </div>

          <button
            type="submit"
            className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
          >
            Create Account
          </button>
        </form>

        <p className="text-sm text-[#8A8473] text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-[#D4A843] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
