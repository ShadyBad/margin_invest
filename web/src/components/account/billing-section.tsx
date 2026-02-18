"use client"

import { useEffect, useState } from "react"

interface BillingStatus {
  plan: string
  status: string | null
  current_period_end: string | null
  is_active: boolean
}

const PLAN_BADGES: Record<string, { label: string; className: string }> = {
  scout: {
    label: "Scout",
    className: "bg-bg-subtle text-text-secondary border-border-primary",
  },
  operator: {
    label: "Operator",
    className: "bg-accent/10 text-accent border-accent/30",
  },
  allocator: {
    label: "Allocator",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
}

const STATUS_PILLS: Record<string, { label: string; className: string }> = {
  active: { label: "Active", className: "bg-green-500/10 text-green-400" },
  trialing: { label: "Trialing", className: "bg-blue-500/10 text-blue-400" },
  past_due: { label: "Past Due", className: "bg-amber-500/10 text-amber-400" },
  canceled: { label: "Canceled", className: "bg-red-500/10 text-red-400" },
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export function BillingSection() {
  const [status, setStatus] = useState<BillingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load billing status")
        return r.json()
      })
      .then(setStatus)
      .catch(() => setError("Unable to load billing information."))
      .finally(() => setLoading(false))
  }, [])

  async function handleCheckout(plan: string) {
    setActionLoading(plan)
    try {
      const resp = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      })
      const data = await resp.json()
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      }
    } finally {
      setActionLoading(null)
    }
  }

  async function handlePortal() {
    setActionLoading("portal")
    try {
      const resp = await fetch("/api/v1/billing/portal", { method: "POST" })
      const data = await resp.json()
      if (data.portal_url) {
        window.location.href = data.portal_url
      }
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Billing</h2>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-bg-subtle rounded w-1/3" />
          <div className="h-4 bg-bg-subtle rounded w-1/4" />
        </div>
      </section>
    )
  }

  if (error || !status) {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Billing</h2>
        <p className="text-sm text-text-secondary">
          {error || "Unable to load billing information."}
        </p>
      </section>
    )
  }

  const planBadge = PLAN_BADGES[status.plan] || PLAN_BADGES.scout
  const statusPill = status.status ? STATUS_PILLS[status.status] : null
  const isCanceled = status.status === "canceled"
  const isPastDue = status.status === "past_due"

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Billing</h2>

      {/* Plan & Status Row */}
      <div className="flex items-center gap-3 mb-4">
        <span
          className={`inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full border ${planBadge.className}`}
        >
          {planBadge.label}
        </span>
        {statusPill && (
          <span
            className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${statusPill.className}`}
          >
            {statusPill.label}
          </span>
        )}
      </div>

      {/* Renewal / Access Info */}
      {status.current_period_end && (
        <p className="text-sm text-text-secondary mb-4">
          {isCanceled
            ? `Access until ${formatDate(status.current_period_end)}`
            : `Renews ${formatDate(status.current_period_end)}`}
        </p>
      )}

      {/* Past Due Warning */}
      {isPastDue && (
        <div className="rounded-sm border border-amber-500/30 bg-amber-500/5 p-3 mb-4">
          <p className="text-sm text-amber-400">
            Your payment method needs updating.{" "}
            <button
              onClick={handlePortal}
              className="underline hover:text-amber-300 transition-colors"
            >
              Update payment method
            </button>
          </p>
        </div>
      )}

      {/* Actions */}
      {status.plan === "scout" ? (
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => handleCheckout("operator")}
            disabled={actionLoading !== null}
            className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading === "operator" ? "Loading..." : "Upgrade to Operator - $29/mo"}
          </button>
          <button
            onClick={() => handleCheckout("allocator")}
            disabled={actionLoading !== null}
            className="px-4 py-2 bg-amber-500 text-bg-primary font-medium text-sm rounded-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading === "allocator" ? "Loading..." : "Upgrade to Allocator - $79/mo"}
          </button>
        </div>
      ) : (
        <button
          onClick={handlePortal}
          disabled={actionLoading !== null}
          className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm hover:bg-bg-subtle transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {actionLoading === "portal" ? "Loading..." : "Manage subscription"}
        </button>
      )}
    </section>
  )
}
