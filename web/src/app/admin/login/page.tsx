"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

type Step = "credentials" | "mfa"

export default function AdminLoginPage() {
  const router = useRouter()

  // Step 1 state
  const [email, setEmail] = useState("")
  const [pw, setPw] = useState("")

  // Step 2 state
  const [totpCode, setTotpCode] = useState("")
  const [challengeStr, setChallengeStr] = useState<string | null>(null)

  // Shared state
  const [step, setStep] = useState<Step>("credentials")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? ""

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await fetch(`${apiBase}/api/v1/auth/admin-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, pw }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail ?? data.message ?? "Invalid credentials")
        return
      }

      const data = await res.json()
      if (data.mfa_required) {
        setChallengeStr(data.challenge_str ?? null)
        setStep("mfa")
      } else {
        router.push("/admin/approvals")
      }
    } catch {
      setError("Unable to reach the server. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await fetch(`${apiBase}/api/v1/auth/admin-mfa-complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ totp_code: totpCode, challenge_str: challengeStr }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail ?? data.message ?? "Invalid code")
        return
      }

      router.push("/admin/approvals")
    } catch {
      setError("Unable to reach the server. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      data-testid="admin-login-page"
      className="min-h-screen flex items-center justify-center bg-zinc-950"
    >
      <div className="w-full max-w-sm px-4">
        {/* Header */}
        <div className="mb-8 text-center">
          <p className="font-mono text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">
            Margin Invest
          </p>
          <h1 className="font-mono text-xl font-semibold text-zinc-100">
            Admin Console
          </h1>
        </div>

        {/* Card */}
        <div className="terminal-card p-6 space-y-5">
          {/* Step indicator */}
          <div className="flex items-center gap-2 pb-1">
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-semibold ${
                step === "credentials"
                  ? "bg-accent text-white"
                  : "bg-bg-subtle text-text-secondary"
              }`}
            >
              1
            </span>
            <span
              className={`text-xs font-mono ${
                step === "credentials" ? "text-zinc-300" : "text-zinc-600"
              }`}
            >
              Credentials
            </span>
            <span className="text-zinc-700 font-mono text-xs mx-1">—</span>
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-semibold ${
                step === "mfa"
                  ? "bg-accent text-white"
                  : "bg-bg-subtle text-text-secondary"
              }`}
            >
              2
            </span>
            <span
              className={`text-xs font-mono ${
                step === "mfa" ? "text-zinc-300" : "text-zinc-600"
              }`}
            >
              Authenticator
            </span>
          </div>

          {/* Error banner */}
          {error && (
            <div
              data-testid="error-banner"
              className="px-3 py-2.5 rounded-lg bg-red-950 border border-red-800 text-red-300 text-sm font-mono"
            >
              {error}
            </div>
          )}

          {/* Step 1: Credentials form */}
          {step === "credentials" && (
            <form
              data-testid="credentials-form"
              onSubmit={handleCredentialsSubmit}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <label
                  htmlFor="admin-email"
                  className="block text-xs font-mono text-zinc-400 uppercase tracking-wider"
                >
                  Email
                </label>
                <input
                  id="admin-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                  placeholder="admin@example.com"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="admin-pw"
                  className="block text-xs font-mono text-zinc-400 uppercase tracking-wider"
                >
                  Password
                </label>
                <input
                  id="admin-pw"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={pw}
                  onChange={(e) => setPw(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-accent text-white font-mono text-sm font-semibold tracking-wide hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Verifying..." : "Continue"}
              </button>
            </form>
          )}

          {/* Step 2: MFA form */}
          {step === "mfa" && (
            <form
              data-testid="mfa-form"
              onSubmit={handleMfaSubmit}
              className="space-y-4"
            >
              <p className="text-xs text-zinc-400 font-mono leading-relaxed">
                Enter the 6-digit code from your authenticator app.
              </p>

              <div className="space-y-1.5">
                <label
                  htmlFor="totp-code"
                  className="block text-xs font-mono text-zinc-400 uppercase tracking-wider"
                >
                  TOTP Code
                </label>
                <input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                  className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors text-center tracking-[0.4em] text-base"
                  placeholder="000000"
                />
              </div>

              <button
                type="submit"
                disabled={loading || totpCode.length !== 6}
                className="w-full py-2.5 rounded-lg bg-accent text-white font-mono text-sm font-semibold tracking-wide hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Verifying..." : "Verify"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("credentials")
                  setError(null)
                  setTotpCode("")
                }}
                className="w-full py-2 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                ← Back to credentials
              </button>
            </form>
          )}
        </div>

        <p className="mt-4 text-center text-[10px] font-mono text-zinc-700 tracking-wider uppercase">
          Restricted access
        </p>
      </div>
    </div>
  )
}
