"use client"

import { useEffect, useState } from "react"

import { CorrelationGrid } from "@/components/ui/correlation-grid"

// Fallback data when API is unavailable
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

  return (
    <CorrelationGrid
      tickers={data.tickers}
      matrix={data.matrix}
      showTooltip={false}
    />
  )
}
