"use client"

import Link from "next/link"

interface MfaStatusProps {
  hasPassword: boolean
  mfaEnabled: boolean
  mfaGraceDeadline: string | null
  oauthProvider: string | null
  onRegenerateCodes?: () => void
  onDisableMfa?: () => void
  regenerating?: boolean
  disabling?: boolean
}

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
}

function formatGraceDeadline(deadline: string): string {
  const deadlineDate = new Date(deadline)
  const now = new Date()
  const diffMs = deadlineDate.getTime() - now.getTime()

  if (diffMs <= 0) return "expired"

  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 1) return "1 day"
  if (diffDays <= 30) return `${diffDays} days`

  return deadlineDate.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

export function MfaStatus({
  hasPassword,
  mfaEnabled,
  mfaGraceDeadline,
  oauthProvider,
  onRegenerateCodes,
  onDisableMfa,
  regenerating = false,
  disabling = false,
}: MfaStatusProps) {
  const providerLabel =
    oauthProvider && PROVIDER_LABELS[oauthProvider]
      ? PROVIDER_LABELS[oauthProvider]
      : oauthProvider || "your OAuth provider"

  // State 1: OAuth-only, no password
  if (!hasPassword && oauthProvider) {
    return (
      <div>
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide mb-3">
          Multi-Factor Authentication
        </h3>
        <p className="text-sm text-text-secondary">
          Multi-factor authentication is managed through your {providerLabel} account.
        </p>
      </div>
    )
  }

  // State 2: Has password, MFA not enabled
  if (hasPassword && !mfaEnabled) {
    const graceExpired = mfaGraceDeadline && new Date(mfaGraceDeadline).getTime() <= Date.now()
    const graceRemaining = mfaGraceDeadline ? formatGraceDeadline(mfaGraceDeadline) : null

    return (
      <div>
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide mb-3">
          Multi-Factor Authentication
        </h3>
        <div className="flex items-center gap-2 mb-2" role="status">
          <span
            className="w-2 h-2 rounded-full bg-amber-500"
            aria-label="MFA status: Not configured"
          />
          <span className="text-sm text-text-primary font-medium">Not configured</span>
        </div>
        <p className="text-sm text-text-secondary mb-3">
          Multi-factor authentication adds a second layer of verification when you sign in with
          your password. It&apos;s required for password-based accounts.
        </p>

        {mfaGraceDeadline && !graceExpired && (
          <div
            className="rounded-sm border border-amber-500/30 bg-amber-500/5 p-3 mb-3"
            role="alert"
          >
            <p className="text-sm text-amber-400">
              You have {graceRemaining} to set up MFA before access is restricted.
            </p>
          </div>
        )}

        {mfaGraceDeadline && graceExpired && (
          <div
            className="rounded-sm border border-red-500/30 bg-red-500/5 p-3 mb-3"
            role="alert"
          >
            <p className="text-sm text-red-400">
              Your MFA grace period has expired. Set up MFA now to continue using your account.
            </p>
          </div>
        )}

        <Link
          href="/mfa/setup"
          className="inline-flex px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
        >
          Set Up MFA
        </Link>
      </div>
    )
  }

  // State 3: Has password, MFA enabled
  if (hasPassword && mfaEnabled) {
    return (
      <div>
        <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide mb-3">
          Multi-Factor Authentication
        </h3>
        <div className="flex items-center gap-2 mb-2" role="status">
          <span
            className="w-2 h-2 rounded-full bg-emerald-500"
            aria-label="MFA status: Enabled"
          />
          <span className="text-sm text-text-primary font-medium">
            Enabled &mdash; Authenticator app
          </span>
        </div>
        <p className="text-sm text-text-secondary mb-3">
          Your account is protected by an authenticator app.
        </p>
        <div className="flex flex-wrap gap-3">
          {onRegenerateCodes && (
            <button
              onClick={onRegenerateCodes}
              disabled={regenerating}
              className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm hover:bg-bg-subtle transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {regenerating ? "Regenerating..." : "Regenerate Recovery Codes"}
            </button>
          )}
          {onDisableMfa && (
            <button
              onClick={onDisableMfa}
              disabled={disabling}
              className="px-4 py-2 text-red-400 font-medium text-sm hover:text-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {disabling ? "Removing..." : "Remove MFA"}
            </button>
          )}
        </div>
      </div>
    )
  }

  // Fallback: no password, no OAuth (shouldn't happen, but handle gracefully)
  return (
    <div>
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide mb-3">
        Multi-Factor Authentication
      </h3>
      <p className="text-sm text-text-secondary">
        Set a password to enable multi-factor authentication.
      </p>
    </div>
  )
}
