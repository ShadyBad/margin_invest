import type { CandidateCard } from "../shared/types"
import { FactorBars } from "../visualizations/factor-bars"

interface SystemReportCardProps {
  candidate: CandidateCard | null
}

/**
 * Returns the CSS color for a given composite tier.
 * Matches the project's 5-tier percentile tokens.
 */
function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional":
      return "var(--color-percentile-exceptional)"
    case "high":
      return "var(--color-percentile-strong)"
    case "medium":
      return "var(--color-percentile-average)"
    case "low":
    case "below":
      return "var(--color-percentile-below)"
    case "none":
    case "weak":
      return "var(--color-percentile-weak)"
    default:
      return "var(--color-text-primary)"
  }
}

/**
 * Formats a scored_at ISO string into a relative time string (e.g. "2h ago").
 */
function formatRelativeTime(isoString: string): string {
  const scored = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - scored.getTime()

  if (diffMs < 0) return "just now"

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function SystemReportCard({ candidate }: SystemReportCardProps) {
  const hasCand = candidate !== null

  return (
    <div
      data-hero-card
      className="terminal-card w-full max-w-sm"
      style={{
        boxShadow: "0 0 40px rgba(26,122,90,0.08)",
      }}
    >
      {/* Header strip */}
      <div
        className="flex items-center gap-2 px-5 py-3"
        style={{
          borderBottom: "1px solid var(--color-border-subtle)",
        }}
      >
        {/* Status dot */}
        <span
          className="inline-block w-2 h-2 rounded-full shrink-0"
          data-testid="status-dot"
          style={{
            backgroundColor: hasCand
              ? "var(--color-bullish)"
              : "var(--color-text-tertiary)",
          }}
        />
        <span className="text-mono-label text-text-tertiary">SYSTEM REPORT</span>
      </div>

      {/* Body */}
      <div className="px-5 py-5">
        {/* Ticker + Name row */}
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-title-1 text-text-primary">
            {hasCand ? candidate.ticker : "\u2014"}
          </span>
          <span className="text-caption text-text-secondary truncate">
            {hasCand ? candidate.name : "\u2014"}
          </span>
        </div>

        {/* Composite score */}
        <div className="mb-5">
          <span
            className="text-mono-data font-bold"
            style={{
              color: hasCand
                ? getTierColor(candidate.composite_tier)
                : "var(--color-text-tertiary)",
            }}
          >
            {hasCand ? Math.round(candidate.score) : "\u2014"}
          </span>
          <span className="text-caption text-text-tertiary ml-2">
            Composite Score
          </span>
        </div>

        {/* Factor bars */}
        {hasCand ? (
          <FactorBars
            factors={{
              quality: candidate.quality_percentile,
              value: candidate.value_percentile,
              momentum: candidate.momentum_percentile,
              sentiment: candidate.sentiment_percentile,
              growth: candidate.growth_percentile,
            }}
            compact
          />
        ) : (
          <div className="flex flex-col gap-2.5">
            {["QUALITY", "VALUE", "MOMENTUM", "SENTIMENT", "GROWTH"].map(
              (label) => (
                <div key={label} className="flex items-center gap-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-tertiary w-[72px] shrink-0">
                    {label}
                  </span>
                  <div className="relative flex-1 rounded-full bg-white/5 overflow-hidden h-1" />
                  <span className="font-mono text-[11px] text-text-secondary w-7 text-right">
                    {"\u2014"}
                  </span>
                </div>
              )
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--color-border-subtle)" }}>
          <span className="text-caption text-text-tertiary">
            {hasCand
              ? `Scored ${formatRelativeTime(candidate.scored_at)}`
              : "No data available"}
          </span>
        </div>
      </div>
    </div>
  )
}
