"use client"

import { useState } from "react"
import { ConfirmationModal } from "./confirmation-modal"

interface PasswordSectionProps {
  hasPassword: boolean
  oauthProvider: string | null
  linkedProviders: string[]
  passwordLastChanged?: string | null
}

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
}

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays > 30) {
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    })
  }
  if (diffDays > 0) return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`
  if (diffHours > 0) return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`
  if (diffMinutes > 0) return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`
  return "just now"
}

export function PasswordSection({
  hasPassword,
  oauthProvider,
  linkedProviders,
  passwordLastChanged,
}: PasswordSectionProps) {
  const [mode, setMode] = useState<"idle" | "set" | "change">("idle")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [removing, setRemoving] = useState(false)
  const [removeModalOpen, setRemoveModalOpen] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)

  const providerLabel =
    oauthProvider && PROVIDER_LABELS[oauthProvider]
      ? PROVIDER_LABELS[oauthProvider]
      : oauthProvider || "your OAuth provider"

  const hasLinkedProviders = linkedProviders.length > 0

  function resetForm() {
    setMode("idle")
    setCurrentPassword("")
    setNewPassword("")
    setConfirmPassword("")
    setError(null)
  }

  async function handleSetPassword(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }

    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters.")
      return
    }

    setSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/set-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: newPassword }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to set password" }))
        throw new Error(data.detail ?? data.message ?? "Failed to set password")
      }

      setSuccess("Password set successfully.")
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set password")
    } finally {
      setSubmitting(false)
    }
  }

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
        throw new Error(data.detail ?? data.message ?? "Password change failed")
      }

      setSuccess("Password updated. Other sessions have been signed out.")
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemovePassword(values: Record<string, string>) {
    const password = values.password
    if (!password) return
    setError(null)
    setSuccess(null)
    setModalError(null)
    setRemoving(true)
    try {
      const res = await fetch("/api/v1/auth/remove-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to remove password" }))
        throw new Error(data.detail ?? data.message ?? "Failed to remove password")
      }
      setSuccess("Password removed. You can now sign in with your linked provider only.")
      setRemoveModalOpen(false)
      resetForm()
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to remove password")
    } finally {
      setRemoving(false)
    }
  }

  // No password state
  if (!hasPassword) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className={`w-2 h-2 rounded-full ${hasPassword ? "bg-emerald-500" : "bg-amber-500"}`} />
          <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide">
            Password
          </h3>
        </div>
        <p className="text-sm text-text-secondary mb-3">
          You don&apos;t have a password on this account. Add one to sign in with your email and
          password as an alternative to {providerLabel}.
        </p>

        {error && <p className="text-sm text-red-400 mb-3">{error}</p>}
        {success && <p className="text-sm text-green-400 mb-3">{success}</p>}

        {mode === "set" ? (
          <form onSubmit={handleSetPassword} className="space-y-3 max-w-sm">
            <div>
              <label htmlFor="new-password" className="block text-sm text-text-secondary mb-1">
                New password
              </label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={12}
                className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label
                htmlFor="confirm-password"
                className="block text-sm text-text-secondary mb-1"
              >
                Confirm password
              </label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={12}
                className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={submitting || !newPassword || !confirmPassword}
                className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? "Setting..." : "Set Password"}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 text-text-secondary font-medium text-sm hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setMode("set")}
            className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-lg hover:bg-accent-hover transition-colors"
          >
            Set Password
          </button>
        )}
      </div>
    )
  }

  // Has password state
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className={`w-2 h-2 rounded-full ${hasPassword ? "bg-emerald-500" : "bg-amber-500"}`} />
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide">
          Password
        </h3>
      </div>
      {passwordLastChanged && (
        <p className="text-sm text-text-secondary mb-3">
          Password last changed {formatRelativeTime(passwordLastChanged)}.
        </p>
      )}

      {error && <p className="text-sm text-red-400 mb-3">{error}</p>}
      {success && <p className="text-sm text-green-400 mb-3">{success}</p>}

      {mode === "change" ? (
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
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="block text-sm text-text-secondary mb-1">
              New password
            </label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={12}
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
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
              className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none"
            />
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting || !currentPassword || !newPassword || !confirmPassword}
              className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Updating..." : "Update Password"}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="px-4 py-2 text-text-secondary font-medium text-sm hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setMode("change")}
            className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-lg hover:bg-bg-subtle transition-colors"
          >
            Change Password
          </button>
          {hasLinkedProviders && (
            <button
              onClick={() => setRemoveModalOpen(true)}
              disabled={removing}
              className="px-4 py-2 text-red-400 font-medium text-sm hover:text-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {removing ? "Removing..." : "Remove Password"}
            </button>
          )}
        </div>
      )}

      <ConfirmationModal
        open={removeModalOpen}
        title="Remove Password"
        description="Enter your current password to remove it. You'll only be able to sign in with your linked provider."
        fields={[{ name: "password", label: "Current password", type: "password" }]}
        onClose={() => { setRemoveModalOpen(false); setModalError(null) }}
        onConfirm={handleRemovePassword}
        confirmLabel="Remove"
        confirmVariant="danger"
        loading={removing}
        error={modalError}
      />
    </div>
  )
}
