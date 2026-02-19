"use client"

import { Suspense, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { QRCodeSVG } from "qrcode.react"
import { startRegistration } from "@simplewebauthn/browser"

// Use relative URL — proxied to backend via Vercel/Next.js rewrites

type Step = "choose" | "totp" | "webauthn"

function MfaSetupContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const userId = searchParams.get("userId")
  const challengeToken = searchParams.get("challengeToken")

  const [step, setStep] = useState<Step>("choose")
  const [provisioningUri, setProvisioningUri] = useState("")
  const [secretId, setSecretId] = useState<number | null>(null)
  const [verificationCode, setVerificationCode] = useState("")
  const [error, setError] = useState("")

  const handleChooseAuthenticator = async () => {
    setError("")
    try {
      const res = await fetch(`/api/v1/auth/mfa/setup-totp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: Number(userId), challenge_token: challengeToken }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || "Failed to set up TOTP")
        return
      }

      const data = await res.json()
      setProvisioningUri(data.provisioning_uri)
      setSecretId(data.secret_id)
      setStep("totp")
    } catch {
      setError("An unexpected error occurred")
    }
  }

  const handleChooseSecurityKey = () => {
    setStep("webauthn")
  }

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      const res = await fetch(`/api/v1/auth/mfa/confirm-totp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret_id: secretId, code: verificationCode }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || "Invalid verification code")
        return
      }

      router.push("/login")
    } catch {
      setError("An unexpected error occurred")
    }
  }

  const handleRegisterSecurityKey = async () => {
    setError("")
    try {
      const optionsRes = await fetch(
        `/api/v1/auth/mfa/register-webauthn`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: Number(userId), challenge_token: challengeToken }),
        }
      )

      if (!optionsRes.ok) {
        const data = await optionsRes.json()
        setError(data.detail || "Failed to get registration options")
        return
      }

      const { options } = await optionsRes.json()
      await startRegistration(options)

      // WebAuthn registration verification endpoint is not yet implemented.
      setError("WebAuthn registration is not yet available. Please use an authenticator app.")
      setStep("choose")
    } catch {
      setError("An unexpected error occurred")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">Set Up MFA</h1>
        <p className="text-[#8A8473] text-center">
          Multi-factor authentication is required to secure your account. Choose
          your preferred method below.
        </p>

        {error && (
          <p className="text-red-400 text-sm w-full text-center">{error}</p>
        )}

        {step === "choose" && (
          <div className="flex flex-col gap-4 w-full">
            <button
              onClick={handleChooseAuthenticator}
              className="w-full px-4 py-4 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors text-left"
            >
              <span className="font-semibold block">Authenticator App</span>
              <span className="text-sm text-[#8A8473]">
                Google Authenticator, Authy, or 1Password
              </span>
            </button>
            <button
              onClick={handleChooseSecurityKey}
              className="w-full px-4 py-4 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors text-left"
            >
              <span className="font-semibold block">Security Key</span>
              <span className="text-sm text-[#8A8473]">
                YubiKey, fingerprint, or passkey
              </span>
            </button>
          </div>
        )}

        {step === "totp" && (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-[#8A8473] text-sm text-center">
              Scan this QR code with your authenticator app, then enter the
              verification code below.
            </p>
            <div className="bg-white p-4 rounded-sm">
              <QRCodeSVG value={provisioningUri} size={200} />
            </div>
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
                Verify &amp; Enable
              </button>
            </form>
          </div>
        )}

        {step === "webauthn" && (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-[#8A8473] text-sm text-center">
              Register a security key, biometric device, or passkey. You will be
              prompted by your browser to complete registration.
            </p>
            <button
              onClick={handleRegisterSecurityKey}
              className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
            >
              Register Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MfaSetupPage() {
  return (
    <Suspense>
      <MfaSetupContent />
    </Suspense>
  )
}
