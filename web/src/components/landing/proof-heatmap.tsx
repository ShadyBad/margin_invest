"use client"

import { useEffect, useState } from "react"
import { CorrelationGrid } from "@/components/ui/correlation-grid"

const FALLBACK_TICKERS = ["AAPL", "MSFT", "JNJ", "COST", "V"]
const FALLBACK_MATRIX: (number | null)[][] = [
  [1.0, 0.82, 0.15, 0.28, 0.45],
  [0.82, 1.0, 0.12, 0.31, 0.51],
  [0.15, 0.12, 1.0, 0.62, 0.22],
  [0.28, 0.31, 0.62, 1.0, 0.35],
  [0.45, 0.51, 0.22, 0.35, 1.0],
]

interface ShowcaseData {
  tickers: string[]
  matrix: (number | null)[][]
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

export function ProofHeatmap() {
  const [data, setData] = useState<ShowcaseData>({
    tickers: FALLBACK_TICKERS,
    matrix: FALLBACK_MATRIX,
  })

  useEffect(() => {
    async function fetchShowcase() {
      try {
        const resp = await fetch("/api/v1/correlations/showcase")
        if (resp.ok) {
          const json = await resp.json()
          setData({ tickers: json.tickers, matrix: json.matrix })
        }
      } catch {
        // Keep fallback
      }
    }
    fetchShowcase()
  }, [])

  const interpretation = interpretCorrelation(data.matrix)

  return (
    <div>
      <CorrelationGrid
        tickers={data.tickers}
        matrix={data.matrix}
        showTooltip={false}
      />
      {interpretation && (
        <p className="text-[10px] text-text-secondary mt-3 text-center font-mono">
          {interpretation}
        </p>
      )}
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Correlations shift during market stress. Past correlation does not guarantee future
        diversification.
      </p>
    </div>
  )
}
