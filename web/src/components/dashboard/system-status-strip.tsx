import type { DashboardResponse } from "@/lib/api/types"

interface SystemStatusStripProps {
  data: DashboardResponse | null
}

function formatTimeAgo(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffMinutes < 1) return "JUST NOW"
  if (diffMinutes < 60) return `${diffMinutes}M AGO`
  if (diffHours < 24) return `${diffHours}H AGO`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return "1D AGO"
  return `${diffDays}D AGO`
}

export function SystemStatusStrip({ data }: SystemStatusStripProps) {
  if (!data) {
    return (
      <div
        className="h-12 bg-bg-elevated border border-border-subtle rounded-lg flex items-center px-4 gap-3"
        data-testid="system-status-strip"
      >
        <span className="w-2 h-2 rounded-full bg-text-tertiary flex-shrink-0" />
        <span className="font-mono text-xs tracking-wider text-text-tertiary">
          SYSTEM OFFLINE &middot; AWAITING CONNECTION
        </span>
      </div>
    )
  }

  const cycleTime = data.last_updated ? formatTimeAgo(data.last_updated) : "UNKNOWN"
  const scored = data.total_scored?.toLocaleString("en-US") ?? "0"
  const surviving = data.picks?.length ?? 0

  return (
    <div
      className="h-12 bg-bg-elevated border border-border-subtle rounded-lg flex items-center px-4 gap-3"
      data-testid="system-status-strip"
    >
      <span className="w-2 h-2 rounded-full bg-bullish animate-pulse flex-shrink-0" />
      <span className="font-mono text-xs tracking-wider text-text-secondary">
        SCORED {scored} &middot; SURVIVING {surviving} &middot; LAST RUN {cycleTime}
      </span>
    </div>
  )
}
