export interface ScoreChange {
  ticker: string
  previousScore: number
  currentScore: number
  changedAt: string
}

interface RecentChangesProps {
  changes: ScoreChange[]
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr.includes("T") ? dateStr : dateStr + "T00:00:00")
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function formatDelta(delta: number): string {
  if (delta > 0) return `(+${delta})`
  if (delta < 0) return `(${delta})`
  return "(0)"
}

function deltaClass(delta: number): string {
  if (delta > 0) return "text-bullish"
  if (delta < 0) return "text-warning"
  return "text-text-secondary"
}

export function RecentChanges({ changes }: RecentChangesProps) {
  if (changes.length === 0) {
    return (
      <p className="text-sm text-text-tertiary text-center py-6">
        No recent changes
      </p>
    )
  }

  return (
    <div className="divide-y divide-border-subtle">
      {changes.map((change, i) => {
        const delta = change.currentScore - change.previousScore
        return (
          <div
            key={`${change.ticker}-${i}`}
            className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
          >
            <div className="flex items-center gap-3">
              <span className="font-semibold text-text-primary text-sm">
                {change.ticker}
              </span>
              <span className="text-sm text-text-secondary font-mono">
                <span>{change.previousScore}</span>
                <span className="mx-1.5 text-text-tertiary">&rarr;</span>
                <span>{change.currentScore}</span>
              </span>
              <span className={`text-sm font-mono font-medium ${deltaClass(delta)}`}>
                {formatDelta(delta)}
              </span>
            </div>
            <span className="text-xs text-text-tertiary">
              {formatDate(change.changedAt)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
