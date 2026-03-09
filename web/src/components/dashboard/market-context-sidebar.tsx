interface MarketContextSidebarProps {
  pickCount: number
  totalScored: number | null
  universeSize: number | null
  engineVersion?: string
  lastScoringRun?: string | null
}

function formatNumber(value: number | null): string {
  if (value === null || value === undefined) return "\u2014"
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

function StatRow({ label, value, testId }: { label: string; value: string; testId?: string }) {
  return (
    <div className="flex items-baseline justify-between py-1.5">
      <span className="text-xs text-text-tertiary">{label}</span>
      <span className="text-sm font-mono text-text-primary" data-testid={testId}>
        {value}
      </span>
    </div>
  )
}

export function MarketContextSidebar({
  pickCount,
  totalScored,
  universeSize,
  engineVersion,
  lastScoringRun,
}: MarketContextSidebarProps) {
  return (
    <aside className="w-56 shrink-0 hidden lg:block" data-testid="market-context-sidebar">
      <div className="sticky top-24 border border-border-subtle rounded-lg bg-bg-elevated p-4">
        <h3 className="font-mono text-xs uppercase tracking-widest text-text-tertiary mb-3">
          Market Context
        </h3>
        <div className="space-y-0">
          <StatRow label="Universe" value={formatNumber(universeSize)} />
          <StatRow label="Scored" value={formatNumber(totalScored)} />
          <StatRow label="Surviving" value={String(pickCount)} />
          {engineVersion && (
            <StatRow label="Engine" value={engineVersion} />
          )}
          {lastScoringRun && (
            <StatRow
              label="Last Run"
              value={formatTime(lastScoringRun)}
              testId="last-run-value"
            />
          )}
        </div>
      </div>
    </aside>
  )
}
