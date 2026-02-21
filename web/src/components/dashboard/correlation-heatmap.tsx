"use client"

import { useCallback, useEffect, useState } from "react"

import { getCorrelations } from "@/lib/api/correlations"
import type { CorrelationResponse } from "@/lib/api/types"
import { CorrelationGrid } from "@/components/ui/correlation-grid"

type Method = "returns" | "factors"

export function CorrelationHeatmap() {
  const [method, setMethod] = useState<Method>("returns")
  const [data, setData] = useState<CorrelationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async (m: Method) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getCorrelations(m)
      setData(result)
    } catch (err) {
      if (err instanceof Error && err.message.includes("400")) {
        setError("Score at least 2 tickers to see portfolio correlations.")
      } else {
        setError("Unable to load correlations.")
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(method)
  }, [method, fetchData])

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary">
          Portfolio Correlations
        </div>
        {/* Toggle */}
        <div className="flex gap-1 bg-bg-primary rounded-full p-0.5">
          {(["returns", "factors"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMethod(m)}
              className={`text-[10px] font-mono px-3 py-1 rounded-full transition-colors ${
                method === m
                  ? "bg-bg-elevated text-text-primary shadow-sm"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              {m === "returns" ? "Returns" : "Factors"}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="text-[11px] text-text-tertiary font-mono animate-pulse">
            Computing correlations...
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="text-[11px] text-text-tertiary font-mono">{error}</div>
        </div>
      )}

      {data && !loading && !error && (
        <CorrelationGrid
          tickers={data.tickers}
          matrix={data.matrix}
          sampleSizes={data.sample_sizes}
          showTooltip
        />
      )}

      {data && data.excluded.length > 0 && !loading && (
        <div className="mt-3 text-[9px] text-text-tertiary font-mono">
          Excluded: {data.excluded.map((e) => `${e.ticker} (${e.reason})`).join(", ")}
        </div>
      )}
    </div>
  )
}
