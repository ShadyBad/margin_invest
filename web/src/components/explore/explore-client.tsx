"use client"

import Link from "next/link"

interface ScoreItem {
  ticker: string
  name: string
  sector?: string | null
  composite_percentile: number
  composite_tier: string
}

interface ScoreListData {
  scores: ScoreItem[]
  total: number
  page: number
  page_size: number
}

interface ExploreClientProps {
  initialData: ScoreListData
}

function tierColor(tier: string): string {
  switch (tier) {
    case "exceptional": return "text-accent"
    case "high": return "text-[var(--color-bullish)]"
    case "medium": return "text-text-primary"
    case "low": return "text-[var(--color-warning)]"
    default: return "text-text-tertiary"
  }
}

export function ExploreClient({ initialData }: ExploreClientProps) {
  const { scores } = initialData

  if (scores.length === 0) {
    return (
      <div className="terminal-card p-12 text-center">
        <p className="text-text-secondary">No scored assets available right now. Check back after the next scoring cycle.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {scores.map((item) => (
        <Link
          key={item.ticker}
          href={`/asset/${item.ticker}`}
          className="terminal-card p-5 flex items-center justify-between gap-4 hover:bg-bg-elevated/80 transition-colors group block"
        >
          <div className="flex items-center gap-4 min-w-0">
            <span className="text-lg font-mono font-semibold text-text-primary w-16 shrink-0">
              {item.ticker}
            </span>
            <div className="min-w-0">
              <p className="text-sm text-text-primary truncate">{item.name}</p>
              <p className="text-xs text-text-tertiary">{item.sector ?? "—"}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <span className={`text-lg font-mono font-semibold ${tierColor(item.composite_tier)}`}>
                {item.composite_percentile}
              </span>
              <span className="text-xs text-text-tertiary ml-1">/ 100</span>
            </div>
            <span className="text-xs text-text-tertiary group-hover:text-accent transition-colors">
              View &rarr;
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
