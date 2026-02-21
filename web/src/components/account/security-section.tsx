"use client"

import { signIn, useSession } from "next-auth/react"
import { useState } from "react"
import { RecoveryCodesDisplay } from "../mfa/recovery-codes-display"
import { ProviderIcons } from "./provider-icons"
import { PasswordSection } from "./password-section"
import { MfaStatus } from "./mfa-status"

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
}

export function SecuritySection() {
  const { data: session, update } = useSession()
  const authMethod = session?.authMethod
  const oauthProvider = session?.oauthProvider ?? null
  const hasPassword = session?.hasPassword ?? false
  const mfaEnabled = session?.mfaEnabled ?? false
  const mfaGraceDeadline = session?.mfaGraceDeadline ?? null
  const linkedProviders = session?.linkedProviders ?? []

  const [connecting, setConnecting] = useState<string | null>(null)
  const [regenerating, setRegenerating] = useState(false)
  const [disabling, setDisabling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newRecoveryCodes, setNewRecoveryCodes] = useState<string[] | null>(null)

  const providerLabel =
    oauthProvider && PROVIDER_LABELS[oauthProvider]
      ? PROVIDER_LABELS[oauthProvider]
      : oauthProvider || "your OAuth provider"

  const isOAuthOnly = authMethod === "oauth" && !hasPassword

  async function handleConnect(provider: string) {
    setError(null)
    setConnecting(provider)
    try {
      // NextAuth's signIn will redirect to the OAuth provider
      // The oauth-sync callback will create the LinkedProvider record
      await signIn(provider, { callbackUrl: "/account" })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to link provider")
    } finally {
      setConnecting(null)
    }
  }

  async function handleDisconnect(provider: string) {
    setError(null)
    try {
      const res = await fetch(`/api/v1/auth/unlink-provider/${provider}`, {
        method: "DELETE",
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to unlink provider" }))
        throw new Error(data.detail ?? data.message ?? "Failed to unlink provider")
      }
      await update()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink provider")
    }
  }

  async function handleRegenerateCodes() {
    const password = window.prompt("Enter your current password to regenerate recovery codes")
    if (!password) return

    setError(null)
    setRegenerating(true)
    try {
      const res = await fetch("/api/v1/auth/mfa/regenerate-recovery-codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      })
      if (!res.ok) {
        const data = await res
          .json()
          .catch(() => ({ detail: "Failed to regenerate recovery codes" }))
        throw new Error(data.detail ?? data.message ?? "Failed to regenerate recovery codes")
      }
      const data = await res.json()
      setNewRecoveryCodes(data.codes)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to regenerate recovery codes")
    } finally {
      setRegenerating(false)
    }
  }

  async function handleDisableMfa() {
    const password = window.prompt("Enter your current password")
    if (!password) return
    const totpCode = window.prompt("Enter your current TOTP code")
    if (!totpCode) return

    setError(null)
    setDisabling(true)
    try {
      const res = await fetch("/api/v1/auth/mfa/disable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password, totp_code: totpCode }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to disable MFA" }))
        throw new Error(data.detail ?? data.message ?? "Failed to disable MFA")
      }
      await update()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disable MFA")
    } finally {
      setDisabling(false)
    }
  }

  if (!session?.user) {
    return null
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-6">Security</h2>

      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

      <div className="space-y-6">
        {/* Provider Icons Row */}
        <ProviderIcons
          linkedProviders={linkedProviders}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          connecting={connecting}
        />

        {/* OAuth-only message */}
        {isOAuthOnly && (
          <p className="text-sm text-text-secondary">
            Your account is secured by {providerLabel} OAuth. Password and MFA settings are
            managed through your {providerLabel} account.
          </p>
        )}

        {/* Password Section */}
        <div className="border-t border-border-primary pt-6">
          <PasswordSection
            hasPassword={hasPassword}
            oauthProvider={oauthProvider}
            linkedProviders={linkedProviders}
          />
        </div>

        {/* MFA Section */}
        <div className="border-t border-border-primary pt-6">
          <MfaStatus
            hasPassword={hasPassword}
            mfaEnabled={mfaEnabled}
            mfaGraceDeadline={mfaGraceDeadline}
            oauthProvider={oauthProvider}
            onRegenerateCodes={handleRegenerateCodes}
            onDisableMfa={handleDisableMfa}
            regenerating={regenerating}
            disabling={disabling}
          />
        </div>

        {/* Recovery Codes Display (after regeneration) */}
        {newRecoveryCodes && (
          <div className="border-t border-border-primary pt-6">
            <RecoveryCodesDisplay
              codes={newRecoveryCodes}
              onContinue={() => setNewRecoveryCodes(null)}
            />
          </div>
        )}
      </div>
    </section>
  )
}
