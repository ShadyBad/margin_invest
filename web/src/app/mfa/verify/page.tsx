"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { signIn } from "next-auth/react"
import { startAuthentication } from "@simplewebauthn/browser"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type Method = "totp" | "webauthn"

export default function MfaVerifyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const userId = searchParams.get("userId")

  const [method, setMethod] = useState<Method>("totp")
  const [verificationCode, setVerificationCode] = useState("")
  const [error, setError] = useState("")

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/mfa/verify-totp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, code: verificationCode }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || "Invalid verification code")
        return
      }

      const data = await res.json()

      // Retrieve credentials from session storage for second-pass auth
      const username = sessionStorage.getItem("mfa_username") || ""
      const password = sessionStorage.getItem("mfa_password") || ""

      await signIn("credentials", {
        username,
        password,
        mfaToken: data.mfa_token,
        callbackUrl: "/dashboard",
      })
    } catch {
      setError("An unexpected error occurred")
    }
  }

  const handleWebAuthnAuthenticate = async () => {
    setError("")

    try {
      const optionsRes = await fetch(
        `${API_URL}/api/v1/auth/mfa/webauthn/auth-options`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId }),
        }
      )

      if (!optionsRes.ok) {
        const data = await optionsRes.json()
        setError(data.detail || "Failed to get authentication options")
        return
      }

      const options = await optionsRes.json()
      const credential = await startAuthentication({ optionsJSON: options })

      const verifyRes = await fetch(
        `${API_URL}/api/v1/auth/mfa/webauthn/auth-verify`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, credential }),
        }
      )

      if (!verifyRes.ok) {
        const data = await verifyRes.json()
        setError(data.detail || "Security key authentication failed")
        return
      }

      const data = await verifyRes.json()

      const username = sessionStorage.getItem("mfa_username") || ""
      const password = sessionStorage.getItem("mfa_password") || ""

      await signIn("credentials", {
        username,
        password,
        mfaToken: data.mfa_token,
        callbackUrl: "/dashboard",
      })
    } catch {
      setError("An unexpected error occurred")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-sm">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">
          Verify Your Identity
        </h1>

        {error && (
          <p className="text-red-400 text-sm w-full text-center">{error}</p>
        )}

        <div className="flex w-full rounded-lg overflow-hidden border border-[#1E2740]">
          <button
            onClick={() => setMethod("totp")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              method === "totp"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] hover:text-[#E8E4DD]"
            }`}
          >
            Authenticator
          </button>
          <button
            onClick={() => setMethod("webauthn")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              method === "webauthn"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] hover:text-[#E8E4DD]"
            }`}
          >
            Security Key
          </button>
        </div>

        {method === "totp" && (
          <form
            onSubmit={handleVerifyTotp}
            className="flex flex-col gap-3 w-full"
          >
            <div className="flex flex-col gap-1">
              <label
                htmlFor="verification-code"
                className="text-sm text-[#8A8473]"
              >
                Verification Code
              </label>
              <input
                id="verification-code"
                type="text"
                inputMode="numeric"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors text-center text-lg tracking-widest"
                placeholder="000000"
                maxLength={6}
                required
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
            >
              Verify
            </button>
          </form>
        )}

        {method === "webauthn" && (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-[#8A8473] text-sm text-center">
              Use your security key, biometric device, or passkey to verify your
              identity.
            </p>
            <button
              onClick={handleWebAuthnAuthenticate}
              className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
            >
              Authenticate with Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
