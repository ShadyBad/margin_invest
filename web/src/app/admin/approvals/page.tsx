"use client"

import { useState, useEffect, useCallback } from "react"
import { ApprovalCard } from "@/components/admin/approval-card"
import { PipelineStatus } from "@/components/admin/pipeline-status"
import {
  getApprovals,
  approveApproval,
  rejectApproval,
  type Approval,
} from "@/lib/api/governance"

const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? ""

const FILTER_OPTIONS = [
  { id: "staged", label: "Staged" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
  { id: "expired", label: "Expired" },
  { id: "all", label: "All" },
] as const

type FilterStatus = (typeof FILTER_OPTIONS)[number]["id"]

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [filter, setFilter] = useState<FilterStatus>("staged")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rejectTarget, setRejectTarget] = useState<number | null>(null)
  const [rejectReason, setRejectReason] = useState("")

  const fetchApprovals = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const status = filter === "all" ? undefined : filter
      const data = await getApprovals(ADMIN_KEY, status)
      setApprovals(data.approvals)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch approvals")
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchApprovals()
  }, [fetchApprovals])

  const handleApprove = async (id: number) => {
    try {
      await approveApproval(ADMIN_KEY, id)
      setApprovals((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: "approved" } : a))
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve")
    }
  }

  const handleRejectClick = (id: number) => {
    setRejectTarget(id)
    setRejectReason("")
  }

  const handleRejectConfirm = async () => {
    if (rejectTarget === null || !rejectReason.trim()) return
    try {
      await rejectApproval(ADMIN_KEY, rejectTarget, rejectReason.trim())
      setApprovals((prev) =>
        prev.map((a) =>
          a.id === rejectTarget
            ? { ...a, status: "rejected", decision_reason: rejectReason.trim() }
            : a
        )
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject")
    } finally {
      setRejectTarget(null)
      setRejectReason("")
    }
  }

  const handleRejectCancel = () => {
    setRejectTarget(null)
    setRejectReason("")
  }

  return (
    <div data-testid="approvals-page" className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-text-primary mb-1">
        Approval Queue
      </h1>
      <p className="text-sm text-text-tertiary mb-6">
        Review and approve pipeline outputs before publication
      </p>

      {/* Pipeline health monitor */}
      <PipelineStatus adminKey={ADMIN_KEY} />

      {/* Filter buttons */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setFilter(opt.id)}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              filter === opt.id
                ? "bg-accent text-white"
                : "bg-bg-subtle text-text-secondary hover:text-text-primary"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="terminal-card p-4 mb-4 text-bearish text-sm">
          {error}
        </div>
      )}

      {/* Reject reason inline input */}
      {rejectTarget !== null && (
        <div className="terminal-card p-4 mb-4 space-y-3">
          <p className="text-sm text-text-primary font-medium">
            Reject approval #{rejectTarget} — provide a reason:
          </p>
          <input
            type="text"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Reason for rejection (required)"
            className="w-full px-3 py-2 text-sm rounded-lg border border-border-primary bg-bg-primary text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={handleRejectConfirm}
              disabled={!rejectReason.trim()}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-bearish text-white disabled:opacity-50 transition-colors"
            >
              Confirm Reject
            </button>
            <button
              onClick={handleRejectCancel}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-border-primary text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="text-center py-12 text-text-tertiary text-sm">
          Loading approvals...
        </div>
      )}

      {/* Empty state */}
      {!loading && approvals.length === 0 && (
        <div className="text-center py-12 text-text-tertiary text-sm">
          No approvals found for this filter.
        </div>
      )}

      {/* Approval cards */}
      {!loading && approvals.length > 0 && (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onReject={handleRejectClick}
            />
          ))}
        </div>
      )}
    </div>
  )
}
