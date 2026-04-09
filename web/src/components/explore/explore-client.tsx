"use client"

import Link from "next/link"
import { RefreshIcon } from "@/components/icons/refresh-icon"

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

const SAMPLE_SCORES: ScoreItem[] = [
  { ticker: "AAPL", name: "Apple Inc", sector: "Technology", composite_percentile: 82, composite_tier: "exceptional" },
  { ticker: "MSFT", name: "Microsoft Corp", sector: "Technology", composite_percentile: 75, composite_tier: "high" },
  { ticker: "JNJ", name: "Johnson & Johnson", sector: "Healthcare", composite_percentile: 68, composite_tier: "high" },
]

function ScoreCardItem({ item, muted = false }: { item: ScoreItem; muted?: boolean }) {
  return (
    <Link
      href={`/asset/${item.ticker}`}
      className={`terminal-card p-5 flex items-center justify-between gap-4 transition-colors group block ${
        muted ? "opacity-50 pointer-events-none" : "hover:bg-bg-elevated/80"
      }`}
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
        {!muted && (
          <span className="text-xs text-text-tertiary group-hover:text-accent transition-colors">
            View &rarr;
          </span>
        )}
      </div>
    </Link>
  )
}

export function ExploreClient({ initialData }: ExploreClientProps) {
  const { scores } = initialData

  if (scores.length === 0) {
    return (
      <div className="space-y-12">
        {/* Empty state hero section */}
        <div className="text-center">
          <div className="flex justify-center mb-8">
            <div className="text-text-tertiary">
              <RefreshIcon className="w-16 h-16" />
            </div>
          </div>
          <h2 className="text-[28px] md:text-[32px] font-bold text-text-primary mb-3">
            Next cycle runs after market close
          </h2>
          <p className="text-body text-text-secondary max-w-lg mx-auto mb-6">
            Scores update after 4:30 PM ET. The next refresh will be available 2 hours later. Check back then to see the latest rankings.
          </p>
          <Link
            href="/methodology"
            className="inline-block text-sm font-medium text-accent hover:text-accent/80 transition-colors border border-accent/30 rounded px-4 py-2"
          >
            Learn our methodology &rarr;
          </Link>
        </div>

        {/* Sample cards section */}
        <div>
          <p className="text-caption text-text-tertiary mb-4 text-center">Sample data — actual scores coming soon</p>
          <div className="space-y-3 relative">
            {SAMPLE_SCORES.map((item) => (
              <div key={item.ticker} className="relative">
                <ScoreCardItem item={item} muted={true} />
                <div className="absolute inset-0 flex items-center justify-center rounded pointer-events-none">
                  <span className="text-xs font-medium text-text-tertiary bg-bg-primary/60 px-2 py-1 rounded">
                    Sample
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {scores.map((item) => (
        <ScoreCardItem key={item.ticker} item={item} />
      ))}
    </div>
  )
}
