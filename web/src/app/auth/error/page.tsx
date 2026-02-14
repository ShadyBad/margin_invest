"use client"

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

export default function AuthErrorPage() {
  const searchParams = useSearchParams()
  const error = searchParams.get("error")
  const code = searchParams.get("code")

  const message = getErrorMessage(error, code)

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-6 p-8 w-full max-w-sm">
        <div className="w-16 h-16 rounded-full bg-red-400/10 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-400"
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

        <h1 className="text-3xl font-bold text-[#E8E4DD]">
          Authentication Error
        </h1>

        <p className="text-red-400 text-center">{message}</p>

        <Link
          href="/login"
          className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors text-center block"
        >
          Try again
        </Link>
      </div>
    </div>
  )
}
