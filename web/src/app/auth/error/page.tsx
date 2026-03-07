"use client"

import { Suspense } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"

function getErrorMessage(error: string | null, code: string | null): string {
  if (error === "CredentialsSignin") {
    switch (code) {
      case "invalid_credentials":
        return "Invalid username or password."
      case "account_locked":
        return "Your account has been locked due to too many failed attempts. Please try again in 15 minutes."
      case "mfa_required":
        return "Multi-factor authentication is required."
      case "mfa_not_configured":
        return "You must set up MFA before signing in."
      default:
        return "Invalid username or password."
    }
  }

  switch (error) {
    case "AccessDenied":
      return "You do not have permission to sign in."
    case "Configuration":
      return "Server configuration error. Please contact support."
    default:
      return "An error occurred during sign in."
  }
}

function AuthErrorContent() {
  const searchParams = useSearchParams()
  const error = searchParams.get("error")
  const code = searchParams.get("code")

  const message = getErrorMessage(error, code)

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary">
      <div className="flex flex-col items-center gap-6 p-8 w-full max-w-sm">
        <div className="w-16 h-16 rounded-full bg-danger/10 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-danger"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-text-primary">
          Authentication Error
        </h1>

        <p className="text-danger text-center">{message}</p>

        <Link
          href="/login"
          className="w-full px-4 py-3 rounded-sm bg-accent-warm text-white font-semibold hover:opacity-90 transition-opacity text-center block"
        >
          Try again
        </Link>
      </div>
    </div>
  )
}

export default function AuthErrorPage() {
  return (
    <Suspense>
      <AuthErrorContent />
    </Suspense>
  )
}
