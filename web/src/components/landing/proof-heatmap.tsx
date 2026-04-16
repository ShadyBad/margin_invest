"use client"

import { useEffect, useState } from "react"
import { CorrelationGrid } from "@/components/ui/correlation-grid"
import type { CandidateCard } from "./shared/types"

interface ShowcaseData {
  tickers: string[]
  matrix: (number | null)[][]
}

interface ProofHeatmapProps {
  candidates?: CandidateCard[]
}

/**
 * Compute a simple Pearson correlation matrix from candidate factor percentiles.
 * Uses quality, value, momentum as the core factors (sentiment/growth may be null).
 */
function computeClientCorrelation(candidates: CandidateCard[]): ShowcaseData {
  const top5 = candidates.slice(0, 5)
  const tickers = top5.map((c) => c.ticker)
  const n = top5.length

  // Build factor vectors for each candidate (only non-null factors)
  const vectors = top5.map((c) => [
    c.quality_percentile,
    c.value_percentile,
    c.momentum_percentile,
    ...(c.sentiment_percentile != null ? [c.sentiment_percentile] : []),
    ...(c.growth_percentile != null ? [c.growth_percentile] : []),
  ])

  const matrix: (number | null)[][] = Array.from({ length: n }, () =>
    Array(n).fill(null),
  )

  for (let i = 0; i < n; i++) {
    matrix[i][i] = 1.0
    for (let j = i + 1; j < n; j++) {
      const a = vectors[i]
      const b = vectors[j]
      const len = Math.min(a.length, b.length)
      if (len < 2) {
        matrix[i][j] = null
        matrix[j][i] = null
        continue
      }
      const meanA = a.slice(0, len).reduce((s, v) => s + v, 0) / len
      const meanB = b.slice(0, len).reduce((s, v) => s + v, 0) / len
      let num = 0, denA = 0, denB = 0
      for (let k = 0; k < len; k++) {
        const da = a[k] - meanA
        const db = b[k] - meanB
        num += da * db
        denA += da * da
        denB += db * db
      }
      const den = Math.sqrt(denA * denB)
      const r = den > 0 ? num / den : 0
      matrix[i][j] = Math.round(r * 100) / 100
      matrix[j][i] = matrix[i][j]
    }
  }

  return { tickers, matrix }
}

export function interpretCorrelation(matrix: (number | null)[][]): string {
  const n = matrix.length
  let lowPairs = 0
  let highPairs = 0
  let totalPairs = 0

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const val = matrix[i][j]
      if (val == null) continue
      totalPairs++
      const abs = Math.abs(val)
      if (abs < 0.3) lowPairs++
      if (abs > 0.7) highPairs++
    }
  }

  if (totalPairs === 0) return ""
  if (highPairs >= totalPairs * 0.5) {
    return `Caution: ${highPairs} of ${totalPairs} pairs show |ρ| > 0.7 — sector clustering detected.`
  }
  return `${lowPairs} of ${totalPairs} pairs show |ρ| < 0.3 — strong diversification.`
}

export function ProofHeatmap({ candidates = [] }: ProofHeatmapProps) {
  const clientFallback = candidates.length >= 2
    ? computeClientCorrelation(candidates)
    : { tickers: [], matrix: [] as (number | null)[][] }

  const [data, setData] = useState<ShowcaseData>(clientFallback)

  useEffect(() => {
    async function fetchShowcase() {
      try {
        const resp = await fetch("/api/v1/correlations/showcase")
        if (resp.ok) {
          const json = await resp.json()
          setData({ tickers: json.tickers, matrix: json.matrix })
        }
      } catch {
        // Keep client-computed fallback
      }
    }
    fetchShowcase()
  }, [])

  if (data.tickers.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[120px]">
        <span className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
          Correlation data loads after scoring cycle
        </span>
      </div>
    )
  }

  const interpretation = interpretCorrelation(data.matrix)

  return (
    <div aria-label="Correlation matrix between the 5 most recently analyzed candidates">
      <CorrelationGrid
        tickers={data.tickers}
        matrix={data.matrix}
        showTooltip={false}
      />
      {interpretation && (
        <p className="text-xs mt-3 text-center" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
          {interpretation}
        </p>
      )}
      <p className="text-[9px] mt-1 text-center italic" style={{ color: "var(--color-text-tertiary)" }}>
        Correlations shift during market stress. Past correlation does not guarantee future
        diversification.
      </p>
    </div>
  )
}
