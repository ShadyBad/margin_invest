"use client"

import { useState, useEffect } from "react"
import {
  getDashboard,
  getTransparency,
  type DashboardResponse,
  type TransparencyResponse,
} from "@/lib/api/governance"

interface PipelineStatusProps {
  adminKey: string
}

function formatDatetime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function PipelineStatus({ adminKey }: PipelineStatusProps) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [transparency, setTransparency] = useState<TransparencyResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      setLoading(true)
      try {
        const [dashData, transData] = await Promise.all([
          getDashboard(adminKey),
          getTransparency(),
        ])
        if (!cancelled) {
          setDashboard(dashData)
          setTransparency(transData)
        }
      } catch {
        // Silently handle errors — stats will show as "—"
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [adminKey])

  if (loading) {
    return (
      <div data-testid="pipeline-status" className="terminal-card p-5 mb-6">
        <p className="text-sm text-text-tertiary">Loading pipeline status...</p>
      </div>
    )
  }

  const pendingCount = dashboard?.pending_count ?? 0
  const avgLatency = dashboard?.avg_approval_latency_hours
  const rejectionRate = dashboard?.rejection_rate
  const pipelineHealth = transparency?.pipeline_health
  const pipelineStatusValue = pipelineHealth?.status ?? "unknown"
  const lastRun = pipelineHealth?.last_successful_run

  return (
    <div data-testid="pipeline-status" className="terminal-card p-5 mb-6">
      <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider mb-4">
        Pipeline Health
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Pending Approvals */}
        <div>
          <p className="text-xs text-text-secondary mb-1">Pending Approvals</p>
          <p
            data-testid="stat-pending-value"
            className={`text-lg font-mono font-semibold ${
              pendingCount > 0 ? "text-warning" : "text-text-primary"
            }`}
          >
            {pendingCount}
          </p>
        </div>

        {/* Avg Approval Latency */}
        <div>
          <p className="text-xs text-text-secondary mb-1">Avg Approval Latency</p>
          <p
            data-testid="stat-latency-value"
            className="text-lg font-mono font-semibold text-text-primary"
          >
            {avgLatency != null ? `${avgLatency} hours` : "\u2014"}
          </p>
        </div>

        {/* Rejection Rate */}
        <div>
          <p className="text-xs text-text-secondary mb-1">Rejection Rate</p>
          <p
            data-testid="stat-rejection-value"
            className="text-lg font-mono font-semibold text-text-primary"
          >
            {rejectionRate != null ? `${rejectionRate}%` : "\u2014"}
          </p>
        </div>

        {/* Pipeline Status */}
        <div>
          <p className="text-xs text-text-secondary mb-1">Pipeline Status</p>
          <p
            data-testid="stat-pipeline-value"
            className={`text-lg font-mono font-semibold ${
              pipelineStatusValue === "running" ? "text-accent" : "text-text-primary"
            }`}
          >
            {pipelineStatusValue}
          </p>
        </div>

        {/* Last Successful Run */}
        <div>
          <p className="text-xs text-text-secondary mb-1">Last Successful Run</p>
          <p
            data-testid="stat-last-run-value"
            className="text-lg font-mono font-semibold text-text-primary"
          >
            {lastRun ? formatDatetime(lastRun) : "\u2014"}
          </p>
        </div>
      </div>
    </div>
  )
}
