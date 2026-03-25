import { FactorSignature } from "@/components/visualizations/factor-signature"
import { formatScore } from "@/lib/format"
import type { CandidateCard } from "../shared/types"

interface InstrumentPanelProps {
  candidate: CandidateCard | null
}

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

export function InstrumentPanel({ candidate }: InstrumentPanelProps) {
  const hasCand = candidate !== null

  return (
    <div
      data-hero-card
      className="terminal-card w-full max-w-md transition-shadow duration-300 hover:shadow-[0_0_60px_rgba(26,122,90,0.15)]"
      style={{
        boxShadow: "0 0 40px rgba(26,122,90,0.08)",
        borderColor: "rgba(26,122,90,0.2)",
      }}
    >
      {/* Header strip */}
      <div
        className="flex items-center gap-2 px-5 py-3"
        style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
      >
        <span
          className="inline-block w-2 h-2 rounded-full shrink-0"
          data-testid="status-dot"
          style={{
            backgroundColor: hasCand
              ? "var(--color-bullish)"
              : "var(--color-text-tertiary)",
          }}
        />
        <span className="text-mono-label text-text-tertiary">
          {hasCand ? `Live Score — ${candidate.ticker}` : "Live Score"}
        </span>
        {hasCand && (
          <span className="text-mono-label text-text-tertiary ml-auto text-[10px]">
            {formatRelativeTime(candidate.scored_at)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-5">
        {/* Score + ticker header */}
        <div className="flex items-start justify-between mb-1">
          <div>
            <span
              className="font-mono text-[42px] font-bold leading-none tracking-tight inline-block"
              style={{
                color: hasCand
                  ? getTierColor(candidate.composite_tier)
                  : "var(--color-text-tertiary)",
              }}
            >
              {hasCand ? formatScore(candidate.score) : "—"}
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-title-1 text-text-primary">
                {hasCand ? candidate.ticker : "—"}
              </span>
              <span className="text-caption text-text-secondary truncate max-w-[140px]">
                {hasCand ? candidate.name : ""}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              {hasCand && candidate.sector && (
                <span className="text-caption text-text-tertiary">
                  {candidate.sector}
                </span>
              )}
              {hasCand && (
                <span
                  className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded"
                  style={{
                    color: getTierColor(candidate.composite_tier),
                    backgroundColor: `color-mix(in srgb, ${getTierColor(candidate.composite_tier)} 12%, transparent)`,
                  }}
                >
                  {candidate.composite_tier}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Factor Signature */}
        <div className="mt-4">
          {hasCand ? (
            <FactorSignature
              factors={{
                quality: candidate.quality_percentile,
                value: candidate.value_percentile,
                momentum: candidate.momentum_percentile,
                sentiment: candidate.sentiment_percentile,
                growth: candidate.growth_percentile,
              }}
              variant="full"
            />
          ) : (
            <div className="h-[160px] flex items-center justify-center">
              <span className="text-caption text-text-tertiary">
                No data available
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
