/**
 * FactorBars — 5 horizontal percentile bars for scoring factors.
 *
 * Used in: SystemReportCard, Results Stage, Asset Detail.
 * Color tiers match the project's 5-tier percentile encoding
 * (--color-percentile-* tokens in globals.css).
 */

interface FactorBarsProps {
  factors: {
    quality: number // 0-100 percentile
    value: number
    momentum: number
    sentiment: number | null
    growth: number | null
  }
  compact?: boolean // smaller variant for inline use
}

const FACTOR_ORDER = ["quality", "value", "momentum", "sentiment", "growth"] as const

/**
 * Returns a hex color for the given percentile tier.
 * Matches the project's 5-tier encoding from globals.css / panel utils.
 */
function getPercentileColor(score: number): string {
  if (score >= 80) return "#10B981" // exceptional — emerald-500
  if (score >= 60) return "#1C7A5A" // strong — muted emerald
  if (score >= 40) return "#6B7280" // average — gray-500
  if (score >= 20) return "#D97706" // below — amber-600
  return "#DC2626" // weak — red-600
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function FactorBars({ factors, compact = false }: FactorBarsProps) {
  return (
    <div className={`flex flex-col ${compact ? "gap-2.5" : "gap-3"}`}>
      {FACTOR_ORDER.map((key) => {
        const raw = factors[key]
        const isUnavailable = raw === null || raw === undefined

        return (
          <div key={key} className="group/bar flex items-center gap-3 cursor-default">
            {/* Label */}
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-tertiary w-[72px] shrink-0 transition-colors duration-200 group-hover/bar:text-text-secondary">
              {key.toUpperCase()}
            </span>

            {isUnavailable ? (
              <>
                {/* Empty track for unavailable factors */}
                <div
                  className={`relative flex-1 rounded-full bg-white/5 overflow-hidden ${compact ? "h-1" : "h-1.5"}`}
                  data-factor-track
                />
                <span className="font-mono text-[10px] text-text-tertiary w-7 text-right">
                  N/A
                </span>
              </>
            ) : (
              <>
                {/* Bar track */}
                <div
                  className={`relative flex-1 rounded-full bg-white/5 overflow-hidden ${compact ? "h-1" : "h-1.5"} transition-all duration-200 group-hover/bar:bg-white/10`}
                  data-factor-track
                >
                  <div
                    className="h-full rounded-full transition-all duration-500 group-hover/bar:brightness-125"
                    style={{ width: `${clamp(Math.round(raw), 0, 100)}%`, backgroundColor: getPercentileColor(clamp(Math.round(raw), 0, 100)) }}
                    data-factor-bar
                  />
                </div>

                {/* Numeric value */}
                <span className="font-mono text-[11px] text-text-secondary w-7 text-right tabular-nums transition-colors duration-200 group-hover/bar:text-text-primary">
                  {clamp(Math.round(raw), 0, 100)}
                </span>
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
