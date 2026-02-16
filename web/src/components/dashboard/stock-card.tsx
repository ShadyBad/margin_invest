"use client"

import { useState, useCallback } from "react"
import { ActionPill, Sparkline, PercentileBar, ConvictionBadge } from "@/components/ui"
import { AssetDetail } from "./asset-detail"
import { getScore } from "@/lib/api/scores"
import type { PickSummary, ScoreResponse } from "@/lib/api/types"

function formatTimeAgo(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 1) return "< 1h ago"
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

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
        const data = await getScore(pick.ticker, ["price_history", "signal_history"])
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
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
          {pick.data_freshness && pick.data_freshness !== "fresh" && (
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${
                pick.data_freshness === "expired"
                  ? "bg-danger/10 text-danger"
                  : "bg-warning/10 text-warning"
              }`}
              data-testid={`freshness-${pick.ticker}`}
            >
              {pick.data_freshness === "expired"
                ? "Expired"
                : pick.price_updated_at
                  ? `Updated ${formatTimeAgo(pick.price_updated_at)}`
                  : "Stale"}
            </span>
          )}
        </div>
        <ConvictionBadge level={pick.conviction_level} />
      </div>

      <p className="text-sm text-text-secondary mb-4 truncate">{pick.name}</p>

      <div className="flex items-center justify-between mb-4">
        <span className="text-3xl font-bold text-accent">
          {pick.composite_percentile.toFixed(0)}
        </span>
        <ActionPill
          signal={pick.signal}
          buyPrice={pick.buy_price}
          sellPrice={pick.sell_price}
          actualPrice={pick.actual_price}
        />
      </div>

      {/* Price row */}
      <div className="flex items-center justify-between mb-4 text-sm">
        <div className="flex items-center gap-4">
          <span className="text-text-secondary flex items-center gap-1">
            {pick.price_source === "live" && (
              <span
                className="inline-block h-1.5 w-1.5 rounded-full bg-bullish"
                data-testid={`live-price-${pick.ticker}`}
                title="Live price"
              />
            )}
            Price:{" "}
            <span className="text-text-primary font-medium">
              {pick.actual_price != null
                ? `$${pick.actual_price.toFixed(2)}`
                : "N/A"}
            </span>
          </span>
          <span className="text-text-secondary">
            Target:{" "}
            <span className="text-text-primary font-medium">
              {pick.sell_price != null
                ? `$${pick.sell_price.toFixed(2)}`
                : "N/A"}
            </span>
          </span>
          {pick.price_upside != null && (
            <span className={pick.price_upside >= 0 ? "text-bullish" : "text-bearish"}>
              {pick.price_upside >= 0 ? "+" : ""}
              {(pick.price_upside * 100).toFixed(1)}%
            </span>
          )}
        </div>
        <Sparkline
          bars={scoreData?.price_history}
          buyPrice={pick.buy_price}
          sellPrice={pick.sell_price}
        />
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
