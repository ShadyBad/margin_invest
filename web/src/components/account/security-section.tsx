"use client"

import { signIn, useSession } from "next-auth/react"
import { useEffect, useState } from "react"
import { RecoveryCodesDisplay } from "../mfa/recovery-codes-display"
import { ProviderIcons } from "./provider-icons"
import { PasswordSection } from "./password-section"
import { MfaStatus } from "./mfa-status"
import { ConfirmationModal } from "./confirmation-modal"

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

  // Refresh session on mount to get fresh security status from API
  useEffect(() => {
    update()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const [connecting, setConnecting] = useState<string | null>(null)
  const [regenerating, setRegenerating] = useState(false)
  const [disabling, setDisabling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newRecoveryCodes, setNewRecoveryCodes] = useState<string[] | null>(null)
  const [regenModalOpen, setRegenModalOpen] = useState(false)
  const [disableModalOpen, setDisableModalOpen] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)

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

  async function handleRegenerateCodes(values: Record<string, string>) {
    const password = values.password
    if (!password) return
    setError(null)
    setModalError(null)
    setRegenerating(true)
    try {
      const res = await fetch("/api/v1/auth/mfa/regenerate-recovery-codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to regenerate recovery codes" }))
        throw new Error(data.detail ?? data.message ?? "Failed to regenerate recovery codes")
      }
      const data = await res.json()
      setNewRecoveryCodes(data.codes)
      setRegenModalOpen(false)
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to regenerate recovery codes")
    } finally {
      setRegenerating(false)
    }
  }

  async function handleDisableMfa(values: Record<string, string>) {
    const password = values.password
    const totpCode = values.totp
    if (!password || !totpCode) return
    setError(null)
    setModalError(null)
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
      setDisableModalOpen(false)
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to disable MFA")
    } finally {
      setDisabling(false)
    }
  }

  if (!session?.user) {
    return null
  }

  return (
    <section id="security" className="terminal-card p-6 md:p-8">
      <h2 className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6">Security</h2>

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
        <div className="border-t border-border-subtle pt-6">
          <PasswordSection
            hasPassword={hasPassword}
            oauthProvider={oauthProvider}
            linkedProviders={linkedProviders}
          />
        </div>

        {/* MFA Section */}
        <div className="border-t border-border-subtle pt-6">
          <MfaStatus
            hasPassword={hasPassword}
            mfaEnabled={mfaEnabled}
            mfaGraceDeadline={mfaGraceDeadline}
            oauthProvider={oauthProvider}
            onRegenerateCodes={() => { setModalError(null); setRegenModalOpen(true) }}
            onDisableMfa={() => { setModalError(null); setDisableModalOpen(true) }}
            regenerating={regenerating}
            disabling={disabling}
          />
        </div>

        {/* Recovery Codes Display (after regeneration) */}
        {newRecoveryCodes && (
          <div className="border-t border-border-subtle pt-6">
            <RecoveryCodesDisplay
              codes={newRecoveryCodes}
              onContinue={() => setNewRecoveryCodes(null)}
            />
          </div>
        )}
      </div>

      <ConfirmationModal
        open={regenModalOpen}
        title="Regenerate Recovery Codes"
        description="Enter your current password to generate new recovery codes."
        fields={[{ name: "password", label: "Current password", type: "password" }]}
        onClose={() => { setRegenModalOpen(false); setModalError(null) }}
        onConfirm={handleRegenerateCodes}
        confirmLabel="Regenerate"
        loading={regenerating}
        error={modalError}
      />
      <ConfirmationModal
        open={disableModalOpen}
        title="Remove MFA"
        description="Enter your credentials to remove multi-factor authentication."
        fields={[
          { name: "password", label: "Current password", type: "password" },
          { name: "totp", label: "TOTP code", type: "text" },
        ]}
        onClose={() => { setDisableModalOpen(false); setModalError(null) }}
        onConfirm={handleDisableMfa}
        confirmLabel="Remove"
        confirmVariant="danger"
        loading={disabling}
        error={modalError}
      />
    </section>
  )
}
