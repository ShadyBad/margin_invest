import type { DashboardResponse } from "@/lib/api/types"

interface MarketContextPanelProps {
  data: DashboardResponse | null
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "\u2014"
  return value.toLocaleString("en-US")
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) return "< 1h ago"
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return "1d ago"
  return `${diffDays}d ago`
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between py-1.5">
      <span className="text-xs text-text-tertiary">{label}</span>
      <span className="text-sm font-mono text-text-primary">{value}</span>
    </div>
  )
}

/** Compute sector distribution from picks for the mini bar chart */
function getSectorDistribution(data: DashboardResponse): { sector: string; count: number }[] {
  const counts: Record<string, number> = {}
  for (const pick of data.picks) {
    const sector = pick.sector ?? "Unknown"
    counts[sector] = (counts[sector] || 0) + 1
  }
  return Object.entries(counts)
    .map(([sector, count]) => ({ sector, count }))
    .sort((a, b) => b.count - a.count)
}

function SectorBar({ sector, count, maxCount }: { sector: string; count: number; maxCount: number }) {
  const widthPct = maxCount > 0 ? Math.max((count / maxCount) * 100, 8) : 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-text-tertiary w-20 truncate" title={sector}>
        {sector}
      </span>
      <div className="flex-1 h-1.5 bg-border-subtle rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-300"
          style={{ width: `${widthPct}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-text-tertiary w-4 text-right">{count}</span>
    </div>
  )
}

export function MarketContextPanel({ data }: MarketContextPanelProps) {
  const sectors = data ? getSectorDistribution(data) : []
  const maxCount = sectors.length > 0 ? sectors[0].count : 0

  return (
    <aside
      className="w-[280px] shrink-0 hidden lg:block"
      data-testid="market-context-panel"
    >
      <div className="sticky top-20 terminal-card p-4">
        <h3 className="font-mono text-xs uppercase tracking-widest text-text-tertiary mb-3">
          Market Context
        </h3>

        {/* Core stats */}
        <div className="space-y-0 mb-4">
          <StatRow label="Universe" value={formatNumber(data?.universe?.size)} />
          <StatRow label="Scored" value={formatNumber(data?.total_scored)} />
          <StatRow label="Surviving" value={data ? String(data.picks.length) : "\u2014"} />
        </div>

        {/* Cycle info */}
        <div className="border-t border-border-subtle pt-3 mb-4">
          <StatRow
            label="Engine"
            value={data?.universe?.version ?? "\u2014"}
          />
          <StatRow
            label="Last Run"
            value={
              data?.universe?.last_scoring_run
                ? formatTime(data.universe.last_scoring_run)
                : data?.last_updated
                  ? formatTime(data.last_updated)
                  : "\u2014"
            }
          />
        </div>

        {/* Mini sector distribution */}
        {sectors.length > 0 && (
          <div className="border-t border-border-subtle pt-3">
            <span className="font-mono text-[10px] uppercase tracking-widest text-text-tertiary block mb-2">
              Sector Breakdown
            </span>
            <div className="space-y-1.5">
              {sectors.map((s) => (
                <SectorBar key={s.sector} sector={s.sector} count={s.count} maxCount={maxCount} />
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
