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
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      aria-label="Factor percentile distributions across all candidates"
    >
      {distributions.map((d) => (
        <div key={d.label} data-testid={`density-panel-${d.label}`}>
          <span className="text-mono-label text-text-tertiary block mb-2">{d.label}</span>

          {/* Horizontal track with min/median/max dots */}
          <div className="relative h-3 bg-white/5 rounded-full">
            {/* Range bar connecting min to max */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-1 rounded-full bg-accent/30"
              style={{ left: `${d.min}%`, width: `${Math.max(1, d.max - d.min)}%` }}
              data-testid={`density-range-${d.label}`}
            />

            {/* Min dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-text-tertiary"
              style={{ left: `${d.min}%` }}
              title={`Min: ${d.min}`}
              data-testid={`density-min-${d.label}`}
            />

            {/* Median dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-accent"
              style={{ left: `${d.median}%` }}
              title={`Median: ${d.median}`}
              data-testid={`density-median-${d.label}`}
            />

            {/* Max dot */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-text-tertiary"
              style={{ left: `${d.max}%` }}
              title={`Max: ${d.max}`}
              data-testid={`density-max-${d.label}`}
            />
          </div>

          {/* Numeric labels */}
          <div className="flex justify-between mt-1">
            <span className="font-mono text-[10px] text-text-tertiary tabular-nums">{d.min}</span>
            <span className="font-mono text-[10px] text-text-secondary tabular-nums">{d.median}</span>
            <span className="font-mono text-[10px] text-text-tertiary tabular-nums">{d.max}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
