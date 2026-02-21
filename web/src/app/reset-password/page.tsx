"use client"

import { Suspense, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { validatePassword, isPasswordValid } from "@/lib/password-validation"

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const userId = searchParams.get("userId")

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const passwordRules = validatePassword(password)

  if (!token || !userId) {
    return (
      <div className="flex flex-col items-center gap-6">
        <h1 className="text-xl font-semibold text-text-primary">Invalid or missing reset link</h1>
        <Link href="/login" className="text-accent hover:brightness-110 text-[13px]">
          Back to login
        </Link>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!isPasswordValid(password)) {
      setError("Password does not meet all requirements")
      return
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: Number(userId),
          token,
          new_password: password,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? "Password reset failed")
        return
      }

      setSuccess(true)
    } catch {
      setError("Unable to reach the server. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="flex flex-col items-center gap-6">
        <h1 className="text-xl font-semibold text-text-primary">Password reset successfully</h1>
        <p className="text-[13px] text-text-secondary text-center">
          You can now sign in with your new password.
        </p>
        <Link
          href="/login?resetSuccess=true"
          className="h-12 flex items-center justify-center w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 transition-all"
        >
          Sign In
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-text-primary text-center">Reset your password</h1>
      <p className="text-[13px] text-text-secondary text-center mb-2">
        Enter your new password below.
      </p>

      {error && <p className="text-[13px] text-red-400 text-center">{error}</p>}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="new-password" className="text-[13px] font-medium text-text-secondary">
          New Password
        </label>
        <input
          id="new-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
          placeholder="Enter new password"
        />
      </div>

      <div className="flex flex-col gap-1.5 -mt-1">
        {passwordRules.map((rule) => (
          <div key={rule.label} className="flex items-center gap-2">
            <div
              className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
                rule.met ? "bg-green-400" : "bg-white/20"
              }`}
            />
            <span
              className={`text-[12px] transition-colors duration-200 ${
                rule.met ? "text-green-400" : "text-text-secondary"
              }`}
            >
              {rule.label}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="confirm-password" className="text-[13px] font-medium text-text-secondary">
          Confirm Password
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
          placeholder="Re-enter new password"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="h-12 w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 active:scale-[0.98] transition-all duration-150 ease-out disabled:opacity-60 disabled:cursor-not-allowed"
      >
        Reset Password
      </button>

      <Link
        href="/login"
        className="text-[13px] text-text-secondary hover:text-text-primary transition-colors text-center"
      >
        Back to login
      </Link>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <div className="w-[calc(100%-32px)] max-w-[420px] rounded-3xl border border-white/[0.06] bg-[rgba(17,17,19,0.6)] px-8 py-10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-[16px] backdrop-saturate-[1.2]">
        <Suspense>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  )
}
