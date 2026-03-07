"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import { validatePassword, isPasswordValid } from "@/lib/password-validation"

function LogoIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
    >
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )
}

function getAuthErrorMessage(error?: string, code?: string): string | null {
  if (error !== "CredentialsSignin") return null
  switch (code) {
    case "api_unreachable":
      return "Unable to reach the authentication service. Please try again later."
    case "account_locked":
      return "Account locked due to too many failed attempts. Try again in 15 minutes."
    case "invalid_credentials":
    default:
      return "Invalid username or password."
  }
}

interface LoginCardProps {
  initialMode?: "signin" | "signup"
  authError?: string
  authCode?: string
  resetSuccess?: boolean
}

export function LoginCard({ initialMode = "signin", authError, authCode, resetSuccess }: LoginCardProps) {
  const authErrorMessage = getAuthErrorMessage(authError, authCode)
  const [mode, setMode] = useState<"signin" | "signup">(initialMode)
  const [showCredentials, setShowCredentials] = useState(!!authErrorMessage)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [confirmPassword, setConfirmPassword] = useState("")
  const [confirmPasswordError, setConfirmPasswordError] = useState("")
  const [serverError, setServerError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [forgotMode, setForgotMode] = useState(false)
  const [resetSent, setResetSent] = useState(false)
  const [tosAccepted, setTosAccepted] = useState(false)

  const passwordRules = validatePassword(password)

  const resetForm = () => {
    setEmail("")
    setPassword("")
    setShowPassword(false)
    setConfirmPassword("")
    setConfirmPasswordError("")
    setServerError("")
    setForgotMode(false)
    setResetSent(false)
  }

  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    signIn("credentials", {
      username: email,
      password,
      callbackUrl: "/dashboard",
    })
  }

  const handleSignUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError("")
    setConfirmPasswordError("")

    // Client-side validation
    if (!email.trim()) {
      setServerError("Email is required")
      return
    }
    if (!isPasswordValid(password)) {
      setServerError("Password does not meet all requirements")
      return
    }
    if (password !== confirmPassword) {
      setConfirmPasswordError("Passwords do not match")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, email, password }),
      })

      if (!res.ok) {
        let message = "Registration failed"
        try {
          const data = await res.json()
          const detail = data.detail ?? data.message
          if (Array.isArray(detail)) {
            message = detail.map((e: { msg?: string }) => e.msg).join(". ")
          } else if (detail) {
            message = detail
          }
        } catch {
          // Response wasn't JSON (e.g. HTML error page)
        }
        setServerError(message)
        return
      }

      // Success — switch to sign-in mode with success message
      resetForm()
      setMode("signin")
      setSuccessMessage("Account created — sign in to continue")
    } catch {
      setServerError("Unable to reach the server. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError("")
    setIsSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      if (res.ok) {
        setResetSent(true)
      }
    } catch {
      setServerError("Unable to reach the server. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="login-card-enter w-[calc(100%-32px)] max-w-[420px] rounded-3xl border border-white/[0.06] bg-[rgba(17,17,19,0.6)] px-8 py-10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-[16px] backdrop-saturate-[1.2] max-md:px-6 max-md:py-8">
      {/* Logo */}
      <div className="flex justify-center mb-6 text-text-primary opacity-80">
        <LogoIcon />
      </div>

      {/* Heading */}
      <h1 className="text-xl font-semibold tracking-[-0.02em] text-text-primary text-center mb-2">
        {mode === "signin" ? "Sign in to Margin Invest" : "Create your account"}
      </h1>
      <p className="text-[13px] text-text-secondary text-center mb-8">
        {mode === "signin" ? "Access your investment analysis" : "Start analyzing investments today"}
      </p>

      {/* Segmented Control */}
      <div data-testid="segmented-control" className="flex rounded-xl bg-white/[0.04] border border-white/[0.06] p-1 mb-6">
        <button
          type="button"
          onClick={() => { setMode("signin"); resetForm(); setSuccessMessage("") }}
          className={`flex-1 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 ${
            mode === "signin"
              ? "bg-accent text-white shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={() => { setMode("signup"); resetForm(); setSuccessMessage("") }}
          className={`flex-1 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 ${
            mode === "signup"
              ? "bg-accent text-white shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          Sign Up
        </button>
      </div>

      {/* OAuth Icons */}
      <div className="flex justify-center gap-4 mb-6">
        <button
          onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
          className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-primary hover:bg-white/[0.08] hover:scale-105 transition-all duration-200 ease-out"
          aria-label="Sign in with Google"
        >
          <GoogleIcon />
        </button>
        <button
          onClick={() => signIn("github", { callbackUrl: "/dashboard" })}
          className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-primary hover:bg-white/[0.08] hover:scale-105 transition-all duration-200 ease-out"
          aria-label="Sign in with GitHub"
        >
          <GitHubIcon />
        </button>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <span className="text-[12px] font-normal tracking-[0.05em] uppercase text-text-secondary">or</span>
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      {/* Status messages */}
      {resetSuccess && (
        <p className="text-[13px] text-green-400 text-center mb-4">
          Password reset successfully. Sign in with your new password.
        </p>
      )}
      {successMessage && (
        <p className="text-[13px] text-green-400 text-center mb-4">{successMessage}</p>
      )}
      {authErrorMessage && (
        <p className="text-[13px] text-red-400 text-center mb-4">{authErrorMessage}</p>
      )}

      {/* Credentials toggle + form */}
      <div className="grid transition-[grid-template-rows] duration-300 ease-out" style={{ gridTemplateRows: showCredentials ? "1fr" : "0fr" }}>
        <div className="overflow-hidden">
          <form onSubmit={forgotMode && mode === "signin" ? handleForgotSubmit : mode === "signin" ? handleCredentialsSubmit : handleSignUpSubmit} className="flex flex-col gap-4 pb-1">
            {serverError && (
              <p className="text-[13px] text-red-400 text-center">{serverError}</p>
            )}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-[13px] font-medium text-text-secondary">
                Email
              </label>
              <input
                id="email"
                type={mode === "signup" ? "email" : "text"}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
                placeholder="you@example.com"
              />
            </div>
            {!(forgotMode && mode === "signin") && (
              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-[13px] font-medium text-text-secondary">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 pr-11 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors duration-200"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
              </div>
            )}
            {mode === "signin" && !forgotMode && (
              <button
                type="button"
                onClick={() => { setForgotMode(true); setServerError("") }}
                className="text-[13px] text-accent hover:brightness-110 transition-colors self-end -mt-2"
              >
                Forgot password?
              </button>
            )}
            {mode === "signup" && (
              <div className="flex flex-col gap-1.5 -mt-1">
                {passwordRules.map((rule) => (
                  <div key={rule.label} className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
                      rule.met ? "bg-green-400" : "bg-white/20"
                    }`} />
                    <span className={`text-[12px] transition-colors duration-200 ${
                      rule.met ? "text-green-400" : "text-text-secondary"
                    }`}>
                      {rule.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {mode === "signup" && (
              <div className="flex flex-col gap-1.5">
                <label htmlFor="confirmPassword" className="text-[13px] font-medium text-text-secondary">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => { setConfirmPassword(e.target.value); setConfirmPasswordError("") }}
                  onBlur={() => {
                    if (confirmPassword && confirmPassword !== password) {
                      setConfirmPasswordError("Passwords do not match")
                    }
                  }}
                  className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
                  placeholder="Re-enter your password"
                />
                {confirmPasswordError && (
                  <p className="text-[12px] text-red-400">{confirmPasswordError}</p>
                )}
              </div>
            )}
            {mode === "signup" && (
              <label className="flex items-start gap-2 text-[13px] text-text-secondary">
                <input
                  type="checkbox"
                  checked={tosAccepted}
                  onChange={(e) => setTosAccepted(e.target.checked)}
                  className="mt-0.5 accent-accent"
                  data-testid="tos-checkbox"
                />
                <span>
                  I agree to the{" "}
                  <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Terms of Service</a>
                  {" "}and{" "}
                  <a href="/privacy" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Privacy Policy</a>
                </span>
              </label>
            )}
            {resetSent && (
              <p className="text-[13px] text-green-400 text-center">Check your email for a reset link.</p>
            )}
            <button
              type="submit"
              disabled={isSubmitting || (mode === "signup" && !tosAccepted)}
              className="h-12 w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 active:scale-[0.98] transition-all duration-150 ease-out disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {forgotMode && mode === "signin" ? "Send reset link" : mode === "signin" ? "Sign In" : "Create Account"}
            </button>
            {forgotMode && (
              <button
                type="button"
                onClick={() => { setForgotMode(false); setResetSent(false); setServerError("") }}
                className="text-[13px] text-text-secondary hover:text-text-primary transition-colors text-center"
              >
                Back to sign in
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Toggle link */}
      <button
        type="button"
        onClick={() => setShowCredentials(!showCredentials)}
        className="w-full text-center text-[13px] font-medium text-text-secondary hover:text-text-primary transition-colors duration-200 mb-6 py-2.5 border border-border-primary rounded-lg hover:bg-bg-subtle"
      >
        {showCredentials ? "← Back to social login" : "Continue with email →"}
      </button>

    </div>
  )
}
