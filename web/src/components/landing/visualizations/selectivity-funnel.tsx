/**
 * SelectivityFunnel — Vertical funnel showing the filtering pipeline.
 *
 * Renders 4 horizontal bars of decreasing width showing how equities
 * are narrowed down at each stage: Universe -> Eligible -> Scored -> Surviving.
 * Pure CSS/HTML bars with locale-formatted counts.
 */

interface SelectivityFunnelProps {
  universeCount: number
  eligibleCount: number
  scoredCount: number
  survivingCount: number
}

const STAGES = [
  { key: "universe", label: "Universe Screened", propKey: "universeCount" },
  { key: "eligible", label: "Passed Filters", propKey: "eligibleCount" },
  { key: "scored", label: "Scored", propKey: "scoredCount" },
  { key: "surviving", label: "Surviving Candidates", propKey: "survivingCount" },
] as const

/** Map stage index to progressively more intense accent opacity */
const STAGE_COLORS = [
  "rgba(26,122,90,0.15)", // universe — subtle
  "rgba(26,122,90,0.30)", // eligible
  "rgba(26,122,90,0.55)", // scored
  "rgba(26,122,90,0.85)", // surviving — strongest
]

export function SelectivityFunnel({
  universeCount,
  eligibleCount,
  scoredCount,
  survivingCount,
}: SelectivityFunnelProps) {
  const counts: Record<string, number> = {
    universeCount,
    eligibleCount,
    scoredCount,
    survivingCount,
  }

  const max = universeCount || 1

  return (
    <div
      className="flex flex-col gap-2"
      aria-label="Selectivity funnel showing how equities are filtered at each stage"
    >
      {STAGES.map((stage, i) => {
        const count = counts[stage.propKey]
        const widthPct = Math.max(6, (count / max) * 100)

        return (
          <div key={stage.key} data-testid={`funnel-stage-${stage.key}`} className="group/funnel cursor-default">
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-mono-label text-text-tertiary transition-colors duration-200 group-hover/funnel:text-text-secondary">{stage.label}</span>
              <span className="font-mono text-xs text-text-secondary tabular-nums transition-colors duration-200 group-hover/funnel:text-text-primary">
                {count.toLocaleString()}
              </span>
            </div>
            <div
              className="h-5 rounded-sm transition-all duration-200 group-hover/funnel:brightness-125 group-hover/funnel:shadow-[0_0_8px_rgba(26,122,90,0.2)]"
              data-testid={`funnel-bar-${stage.key}`}
              style={{
                width: `${widthPct}%`,
                backgroundColor: STAGE_COLORS[i],
              }}
            />
          </div>
        )
      })}
    </div>
  )
}
