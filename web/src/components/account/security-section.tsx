"use client"

import { useSession } from "next-auth/react"
import { useState } from "react"

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
}

export function SecuritySection() {
  const { data: session } = useSession()
  const authMethod = session?.authMethod
  const oauthProvider = session?.oauthProvider
  const mfaVerified = session?.mfaVerified

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const providerLabel =
    oauthProvider && PROVIDER_LABELS[oauthProvider]
      ? PROVIDER_LABELS[oauthProvider]
      : oauthProvider || "your OAuth provider"

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }

    if (newPassword.length < 12) {
      setError("New password must be at least 12 characters.")
      return
    }

    setSubmitting(true)

    try {
      const res = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Password change failed" }))
        throw new Error(data.detail || "Password change failed")
      }

      setSuccess("Password updated. Other sessions have been signed out.")
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed")
    } finally {
      setSubmitting(false)
    }
  }

  if (!session?.user) {
    return null
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Security</h2>

      {authMethod === "oauth" ? (
        <div className="space-y-2">
          <p className="text-sm text-text-secondary">
            Your account is secured by {providerLabel}. Password and MFA settings are managed
            through your {providerLabel} account.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Change Password */}
          <div>
            <h3 className="text-md font-medium text-text-primary mb-3">Change Password</h3>
            <form onSubmit={handleChangePassword} className="space-y-3 max-w-sm">
              <div>
                <label
                  htmlFor="current-password"
                  className="block text-sm text-text-secondary mb-1"
                >
                  Current password
                </label>
                <input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label
                  htmlFor="new-password"
                  className="block text-sm text-text-secondary mb-1"
                >
                  New password
                </label>
                <input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={12}
                  className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label
                  htmlFor="confirm-password"
                  className="block text-sm text-text-secondary mb-1"
                >
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={12}
                  className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
                />
              </div>

              {error && <p className="text-sm text-red-400">{error}</p>}
              {success && <p className="text-sm text-green-400">{success}</p>}

              <button
                type="submit"
                disabled={submitting || !currentPassword || !newPassword || !confirmPassword}
                className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? "Updating..." : "Update Password"}
              </button>
            </form>
          </div>

          {/* MFA Status */}
          <div className="border-t border-border-primary pt-4">
            <h3 className="text-md font-medium text-text-primary mb-2">
              Multi-Factor Authentication
            </h3>
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  mfaVerified ? "bg-green-400" : "bg-yellow-400"
                }`}
              />
              <span className="text-sm text-text-secondary">
                {mfaVerified ? "MFA is enabled" : "MFA is not configured"}
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
