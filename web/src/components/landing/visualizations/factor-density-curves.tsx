/**
 * FactorDensityCurves — Mini distribution visualizations for 5 scoring factors.
 *
 * Shows min / median / max percentile values as dots on horizontal tracks
 * for each factor across all candidates. Pure CSS/HTML, no SVG.
 */

import type { CandidateCard } from "../shared/types"

interface FactorDensityCurvesProps {
  candidates: CandidateCard[]
}

const FACTORS = [
  { key: "quality_percentile" as const, label: "QUALITY" },
  { key: "value_percentile" as const, label: "VALUE" },
  { key: "momentum_percentile" as const, label: "MOMENTUM" },
  { key: "sentiment_percentile" as const, label: "SENTIMENT" },
  { key: "growth_percentile" as const, label: "GROWTH" },
]

function median(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
}

export interface FactorDistribution {
  label: string
  min: number
  median: number
  max: number
}

export function computeDistributions(candidates: CandidateCard[]): FactorDistribution[] {
  // Filter out candidates with all-zero core percentiles (incomplete data)
  const validCandidates = candidates.filter((c) =>
    (c.quality_percentile ?? 0) > 0 ||
    (c.value_percentile ?? 0) > 0 ||
    (c.momentum_percentile ?? 0) > 0
  )

  return FACTORS.map((f) => {
    const values = validCandidates.map((c) => c[f.key]).filter((v): v is number => v != null && v > 0)
    if (values.length === 0) {
      return { label: f.label, min: 0, median: 50, max: 100 }
    }
    return {
      label: f.label,
      min: Math.min(...values),
      median: Math.round(median(values)),
      max: Math.max(...values),
    }
  })
}

export function FactorDensityCurves({ candidates }: FactorDensityCurvesProps) {
  const distributions = computeDistributions(candidates)

  return (
    <div
      className="flex flex-col gap-3"
      aria-label="Factor percentile distributions across all candidates"
    >
      {distributions.map((d) => (
        <div key={d.label} data-testid={`density-panel-${d.label}`} className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-[0.15em] w-20 shrink-0" style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>{d.label}</span>

          {/* Horizontal track with min/median/max dots */}
          <div className="relative h-3 rounded-sm flex-1" style={{ background: "color-mix(in srgb, var(--color-surface-variant) 10%, transparent)" }}>
            {/* Range bar connecting min to max */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-1 rounded-sm"
              style={{ background: "color-mix(in srgb, var(--color-primary) 30%, transparent)", left: `${d.min}%`, width: `${Math.max(1, d.max - d.min)}%` }}
              data-testid={`density-range-${d.label}`}
            />

            {/* Min dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
              style={{ left: `${d.min}%`, background: "var(--color-text-tertiary)" }}
              title={`Min: ${d.min}`}
              data-testid={`density-min-${d.label}`}
            />

            {/* Median dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full"
              style={{ left: `${d.median}%`, background: "var(--color-primary)" }}
              title={`Median: ${d.median}`}
              data-testid={`density-median-${d.label}`}
            />

            {/* Max dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
              style={{ left: `${d.max}%`, background: "var(--color-text-tertiary)" }}
              title={`Max: ${d.max}`}
              data-testid={`density-max-${d.label}`}
            />
          </div>

          {/* Median value */}
          <span className="text-[10px] tabular-nums w-6 text-right shrink-0" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>{d.median}</span>
        </div>
      ))}
    </div>
  )
}
