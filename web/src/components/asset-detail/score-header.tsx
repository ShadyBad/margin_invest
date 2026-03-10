/**
 * ScoreHeader — Prominent composite score display with tier badge and percentile bar.
 *
 * Shows the composite score in large mono text, color-encoded by tier,
 * with a tier pill badge and a full-width universe percentile bar.
 */

interface ScoreHeaderProps {
  score: number
  tier: string
  percentile: number
}

const TIER_COLORS: Record<string, { text: string; bg: string; border: string; bar: string }> = {
  exceptional: {
    text: "text-[var(--color-percentile-exceptional)]",
    bg: "bg-[var(--color-percentile-exceptional)]/10",
    border: "border-[var(--color-percentile-exceptional)]/30",
    bar: "var(--color-percentile-exceptional)",
  },
  high: {
    text: "text-[var(--color-percentile-strong)]",
    bg: "bg-[var(--color-percentile-strong)]/10",
    border: "border-[var(--color-percentile-strong)]/30",
    bar: "var(--color-percentile-strong)",
  },
  medium: {
    text: "text-[var(--color-percentile-average)]",
    bg: "bg-[var(--color-percentile-average)]/10",
    border: "border-[var(--color-percentile-average)]/30",
    bar: "var(--color-percentile-average)",
  },
  watchlist: {
    text: "text-[var(--color-percentile-below)]",
    bg: "bg-[var(--color-percentile-below)]/10",
    border: "border-[var(--color-percentile-below)]/30",
    bar: "var(--color-percentile-below)",
  },
  none: {
    text: "text-[var(--color-percentile-weak)]",
    bg: "bg-[var(--color-percentile-weak)]/10",
    border: "border-[var(--color-percentile-weak)]/30",
    bar: "var(--color-percentile-weak)",
  },
}

const DEFAULT_TIER = {
  text: "text-text-secondary",
  bg: "bg-white/5",
  border: "border-white/10",
  bar: "var(--color-text-secondary, #A09B93)",
}

export function ScoreHeader({ score, tier, percentile }: ScoreHeaderProps) {
  const tierStyle = TIER_COLORS[tier] ?? DEFAULT_TIER
  const clampedPercentile = Math.max(0, Math.min(100, percentile))

  return (
    <div data-testid="score-header" className="terminal-card p-6 space-y-4">
      {/* Score + tier badge */}
      <div className="flex items-center gap-4">
        <span
          className={`font-mono text-[48px] leading-none font-bold tabular-nums ${tierStyle.text}`}
          data-testid="score-value"
        >
          {Math.round(score)}
        </span>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium uppercase tracking-wider border ${tierStyle.text} ${tierStyle.bg} ${tierStyle.border}`}
          data-testid="tier-badge"
        >
          {tier}
        </span>
      </div>

      {/* Percentile bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-text-tertiary font-mono">
          <span>Universe Percentile</span>
          <span data-testid="percentile-value">
            {Math.round(clampedPercentile)}th
          </span>
        </div>
        <div
          className="relative w-full h-2 rounded-full bg-white/[0.06] overflow-hidden"
          data-testid="percentile-track"
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${clampedPercentile}%`,
              backgroundColor: tierStyle.bar,
            }}
            data-testid="percentile-fill"
          />
        </div>
      </div>
    </div>
  )
}
