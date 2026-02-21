"use client"

import { useSession } from "next-auth/react"
import { useState, useEffect, useCallback } from "react"
import Link from "next/link"

const DISMISS_KEY = "mfa-banner-dismissed"

type Phase = "hidden" | "phase1" | "phase2"

function formatTimeRemaining(ms: number): string {
  const hours = ms / (1000 * 60 * 60)
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    return `${days} day${days === 1 ? "" : "s"}`
  }
  if (hours >= 1) {
    const h = Math.floor(hours)
    return `${h} hour${h === 1 ? "" : "s"}`
  }
  return "less than an hour"
}

function computePhase(
  hasPassword: boolean,
  mfaEnabled: boolean,
  mfaGraceDeadline: string | null,
  linkedProviders: string[],
): { phase: Phase; msRemaining: number } {
  // Not shown for OAuth-only (no password)
  if (!hasPassword && linkedProviders.length > 0) {
    return { phase: "hidden", msRemaining: 0 }
  }

  // Not shown when MFA is already enabled
  if (mfaEnabled) {
    return { phase: "hidden", msRemaining: 0 }
  }

  // Not shown when no grace deadline
  if (!mfaGraceDeadline) {
    return { phase: "hidden", msRemaining: 0 }
  }

  const deadline = new Date(mfaGraceDeadline).getTime()
  const now = Date.now()
  const msRemaining = deadline - now

  // Phase 3: past deadline — modal handles this, not banner
  if (msRemaining <= 0) {
    return { phase: "hidden", msRemaining: 0 }
  }

  // Phase 2: 0-48h remaining
  if (msRemaining <= 48 * 60 * 60 * 1000) {
    return { phase: "phase2", msRemaining }
  }

  // Phase 1: >48h remaining
  return { phase: "phase1", msRemaining }
}

export function MfaEnforcementBanner() {
  const { data: session, status } = useSession()
  const [dismissed, setDismissed] = useState(false)
  const [, setTick] = useState(0)

  // Check sessionStorage on mount
  useEffect(() => {
    try {
      if (sessionStorage.getItem(DISMISS_KEY) === "true") {
        setDismissed(true)
      }
    } catch {
      // sessionStorage not available (SSR)
    }
  }, [])

  // Re-compute phase every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1)
    }, 60_000)
    return () => clearInterval(interval)
  }, [])

  const handleDismiss = useCallback(() => {
    setDismissed(true)
    try {
      sessionStorage.setItem(DISMISS_KEY, "true")
    } catch {
      // sessionStorage not available
    }
  }, [])

  if (status !== "authenticated" || !session) return null

  const { phase, msRemaining } = computePhase(
    session.hasPassword ?? false,
    session.mfaEnabled ?? false,
    session.mfaGraceDeadline ?? null,
    session.linkedProviders ?? [],
  )

  if (phase === "hidden") return null

  // Phase 1: dismissible
  if (phase === "phase1") {
    if (dismissed) return null

    return (
      <div
        className="border-l-2 border-border-primary bg-bg-elevated px-4 py-3 text-sm text-text-secondary flex items-center justify-between"
        data-testid="mfa-enforcement-banner"
      >
        <p>
          Set up multi-factor authentication to secure your account.{" "}
          <Link
            href="/mfa/setup"
            className="text-accent hover:text-accent-hover font-medium"
          >
            Set up now &rarr;
          </Link>
        </p>
        <button
          onClick={handleDismiss}
          className="ml-4 text-text-tertiary hover:text-text-secondary shrink-0"
          aria-label="Dismiss MFA setup reminder"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    )
  }

  // Phase 2: non-dismissible warning
  return (
    <div
      className="border-l-2 border-warning bg-warning/10 px-4 py-3 text-sm text-text-primary flex items-center"
      role="alert"
      data-testid="mfa-enforcement-banner"
    >
      <p>
        MFA is required for password accounts. You have{" "}
        <strong>{formatTimeRemaining(msRemaining)}</strong> to complete setup.{" "}
        <Link
          href="/mfa/setup"
          className="text-accent hover:text-accent-hover font-medium"
        >
          Set up now &rarr;
        </Link>
      </p>
    </div>
  )
}
