"use client"

import { useEffect, useState } from "react"
import { signIn } from "next-auth/react"
import { startAuthentication } from "@simplewebauthn/browser"

type Method = "totp" | "webauthn"

function MfaVerifyContent() {
  const [userId, setUserId] = useState<string | null>(null)
  const [challengeToken, setChallengeToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [method, setMethod] = useState<Method>("totp")
  const [verificationCode, setVerificationCode] = useState("")
  const [showRecovery, setShowRecovery] = useState(false)
  const [recoveryCode, setRecoveryCode] = useState("")
  const [error, setError] = useState("")

  // Fetch challenge data from httpOnly cookie via server route
  useEffect(() => {
    async function fetchChallenge() {
      try {
        const res = await fetch("/api/mfa-challenge")
        if (!res.ok) {
          setError("MFA session expired. Please sign in again.")
          setLoading(false)
          return
        }
        const data = await res.json()
        setUserId(data.userId)
        setChallengeToken(data.challengeToken)
      } catch {
        setError("Unable to load MFA session.")
      } finally {
        setLoading(false)
      }
    }
    fetchChallenge()
  }, [])

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      // Call mfa/complete which reads the httpOnly cookie
      const res = await fetch("/api/v1/auth/mfa/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          totp_code: verificationCode,
        }),
        credentials: "include",
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? data.message ?? "Invalid verification code")
        return
      }

      const data = await res.json()

      // Use the MFA completion token to sign in without re-sending password
      await signIn("credentials", {
        mfaCompletionToken: data.mfa_completion_token,
        callbackUrl: "/dashboard",
      })
    } catch (err) {
      console.error("TOTP verification error:", err)
      setError("Unable to reach the server. Please try again.")
    }
  }

  const handleWebAuthnAuthenticate = async () => {
    setError("")

    try {
      const optionsRes = await fetch(
        `/api/v1/auth/mfa/authenticate-webauthn`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: Number(userId),
            challenge_token: challengeToken,
          }),
        }
      )

      if (!optionsRes.ok) {
        const data = await optionsRes.json()
        setError(data.detail ?? data.message ?? "Failed to get authentication options")
        return
      }

      const { options } = await optionsRes.json()
      await startAuthentication(options)

      // WebAuthn authentication verification endpoint is not yet implemented.
      setError("WebAuthn authentication is not yet available. Please use an authenticator app.")
    } catch (err) {
      console.error("WebAuthn authentication error:", err)
      setError("Unable to reach the server. Please try again.")
    }
  }

  const handleVerifyRecovery = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      // Call mfa/complete which reads the httpOnly cookie
      const res = await fetch("/api/v1/auth/mfa/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recovery_code: recoveryCode,
        }),
        credentials: "include",
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? data.message ?? "Invalid recovery code")
        return
      }

      const data = await res.json()

      // Use the MFA completion token to sign in without re-sending password
      await signIn("credentials", {
        mfaCompletionToken: data.mfa_completion_token,
        callbackUrl: "/dashboard",
      })
    } catch (err) {
      console.error("Recovery code verification error:", err)
      setError("Unable to reach the server. Please try again.")
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
        <p className="text-[#8A8473]">Loading...</p>
      </div>
    )
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

        <div className="flex w-full rounded-sm overflow-hidden border border-[#1E2740]">
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

        {method === "totp" && !showRecovery && (
          <div className="flex flex-col gap-4 w-full">
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
                  className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors text-center text-lg tracking-widest"
                  placeholder="000000"
                  maxLength={6}
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
              >
                Verify
              </button>
            </form>
            <p className="text-sm text-[#8A8473] text-center">
              Lost your authenticator?{" "}
              <button
                type="button"
                onClick={() => setShowRecovery(true)}
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Use a recovery code
              </button>
            </p>
          </div>
        )}

        {method === "totp" && showRecovery && (
          <div className="flex flex-col gap-4 w-full">
            <form
              onSubmit={handleVerifyRecovery}
              className="flex flex-col gap-3 w-full"
            >
              <div className="flex flex-col gap-1">
                <label
                  htmlFor="recovery-code"
                  className="text-sm text-[#8A8473]"
                >
                  Recovery code
                </label>
                <input
                  id="recovery-code"
                  type="text"
                  value={recoveryCode}
                  onChange={(e) => setRecoveryCode(e.target.value)}
                  className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors text-center text-lg tracking-widest font-mono"
                  placeholder="xxxx-xxxx"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
              >
                Verify
              </button>
            </form>
            <p className="text-sm text-[#8A8473] text-center">
              <button
                type="button"
                onClick={() => setShowRecovery(false)}
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Back to authenticator
              </button>
            </p>
            <p className="text-sm text-[#8A8473] text-center">
              Lost your recovery codes too?{" "}
              <a
                href="/support?subject=MFA+recovery"
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Contact support
              </a>
            </p>
          </div>
        )}

        {method === "webauthn" && (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-[#8A8473] text-sm text-center">
              Use your security key, biometric device, or passkey to verify your
              identity.
            </p>
            <button
              onClick={handleWebAuthnAuthenticate}
              className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
            >
              Authenticate with Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MfaVerifyPage() {
  return <MfaVerifyContent />
}
