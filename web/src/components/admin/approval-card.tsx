"use client"

import type { Approval } from "@/lib/api/governance"

interface ApprovalCardProps {
  approval: Approval
  onApprove: (id: number) => void
  onReject: (id: number) => void
}

function statusColor(status: string): string {
  switch (status) {
    case "staged":
      return "text-warning"
    case "approved":
      return "text-bullish"
    case "rejected":
    case "expired":
      return "text-bearish"
    default:
      return "text-text-secondary"
  }
}

function formatTimeRemaining(expiresAt: string | null): string | null {
  if (!expiresAt) return null
  const now = new Date()
  const expiry = new Date(expiresAt)
  const diffMs = expiry.getTime() - now.getTime()
  if (diffMs <= 0) return "Expired"
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  if (hours > 0) return `${hours}h ${minutes}m remaining`
  return `${minutes}m remaining`
}

export function ApprovalCard({ approval, onApprove, onReject }: ApprovalCardProps) {
  const impact = approval.impact_summary
  const isStaged = approval.status === "staged"
  const timeRemaining = isStaged ? formatTimeRemaining(approval.expires_at) : null

  return (
    <div
      data-testid={`approval-card-${approval.id}`}
      className="terminal-card p-5"
    >
      {/* Header: gate type + status */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-mono font-medium text-accent">
          {approval.gate_type}
        </span>
        <span
          data-testid="status-badge"
          className={`text-xs font-mono font-semibold uppercase tracking-wider ${statusColor(approval.status)}`}
        >
          {approval.status}
        </span>
      </div>

      {/* Impact summary */}
      {impact && (
        <div className="text-sm text-text-secondary space-y-1 mb-3">
          {impact.ticker_count != null && (
            <p>{impact.ticker_count as number} tickers</p>
          )}
          {impact.conviction_changes != null && (
            <p>{impact.conviction_changes as number} conviction changes</p>
          )}
          {impact.rank_ic != null && (
            <p>Rank IC: {impact.rank_ic as number}</p>
          )}
          {Array.isArray(impact.added) && impact.added.length > 0 && (
            <p>Added: {(impact.added as string[]).join(", ")}</p>
          )}
          {Array.isArray(impact.removed) && impact.removed.length > 0 && (
            <p>Removed: {(impact.removed as string[]).join(", ")}</p>
          )}
        </div>
      )}

      {/* Time remaining (staged only) */}
      {timeRemaining && (
        <p className="text-xs text-warning mb-3">{timeRemaining}</p>
      )}

      {/* Decision reason (for decided approvals) */}
      {approval.decision_reason && (
        <blockquote className="text-sm text-text-secondary italic border-l-2 border-border-primary pl-3 mb-3">
          &ldquo;{approval.decision_reason}&rdquo;
        </blockquote>
      )}

      {/* Action buttons (staged only) */}
      {isStaged && (
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => onApprove(approval.id)}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors"
          >
            Approve
          </button>
          <button
            onClick={() => onReject(approval.id)}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-bearish text-bearish hover:bg-bearish hover:text-white transition-colors"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  )
}
