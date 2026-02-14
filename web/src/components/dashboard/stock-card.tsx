"use client"

import { useState, useCallback } from "react"
import { PercentileBar, ConvictionBadge, SignalBadge } from "@/components/ui"
import { AssetDetail } from "./asset-detail"
import { getScore } from "@/lib/api/scores"
import type { PickSummary, ScoreResponse } from "@/lib/api/types"

interface StockCardProps {
  pick: PickSummary
  className?: string
}

export function StockCard({ pick, className = "" }: StockCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [scoreData, setScoreData] = useState<ScoreResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleClick = useCallback(async () => {
    if (expanded) {
      setExpanded(false)
      return
    }

    setExpanded(true)

    // Only fetch if we haven't already
    if (!scoreData) {
      setLoading(true)
      setError(null)
      try {
        const data = await getScore(pick.ticker)
        setScoreData(data)
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load details",
        )
      } finally {
        setLoading(false)
      }
    }
  }, [expanded, scoreData, pick.ticker])

  return (
    <div
      className={`bg-bg-elevated border border-border-primary rounded-sm p-6 cursor-pointer transition-all ${expanded ? "col-span-full" : ""} ${className}`}
      data-testid={`stock-card-${pick.ticker}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          handleClick()
        }
      }}
      aria-expanded={expanded}
    >
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
        <ConvictionBadge level={pick.conviction_level} />
      </div>

      <p className="text-sm text-text-secondary mb-4 truncate">{pick.name}</p>

      <div className="flex items-center justify-between mb-4">
        <span className="text-3xl font-bold text-accent">
          {pick.composite_percentile.toFixed(0)}
        </span>
        <SignalBadge signal={pick.signal} />
      </div>

      <div className="space-y-2">
        <PercentileBar value={pick.quality_percentile} label="Quality" />
        <PercentileBar value={pick.value_percentile} label="Value" />
        <PercentileBar value={pick.momentum_percentile} label="Momentum" />
      </div>

      {expanded && loading && (
        <div
          className="border-t border-border-primary mt-4 pt-4 flex items-center justify-center"
          data-testid={`loading-detail-${pick.ticker}`}
        >
          <div className="animate-spin h-6 w-6 border-2 border-accent border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-text-secondary">
            Loading details...
          </span>
        </div>
      )}

      {expanded && error && (
        <div className="border-t border-border-primary mt-4 pt-4">
          <p className="text-sm text-bearish">{error}</p>
        </div>
      )}

      {expanded && scoreData && !loading && (
        <AssetDetail score={scoreData} />
      )}
    </div>
  )
}
