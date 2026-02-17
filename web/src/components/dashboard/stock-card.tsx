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

function getCardTierClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "border-accent/30 rounded-lg"
    case "high":
      return "border-l-2 border-l-accent rounded-lg"
    default:
      return "rounded-lg"
  }
}

function getCardShadow(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "shadow-[0_0_30px_rgba(26,122,90,0.08),0_4px_16px_rgba(0,0,0,0.3)] hover:shadow-[0_0_40px_rgba(26,122,90,0.12),0_6px_20px_rgba(0,0,0,0.35)]"
    default:
      return "shadow-card hover:shadow-card-hover"
  }
}

function getScoreClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "text-[56px] font-display text-accent leading-none tracking-[-0.04em]"
    case "high":
      return "text-[48px] font-display text-text-primary leading-none tracking-[-0.04em]"
    default:
      return "text-[48px] font-display text-text-secondary leading-none tracking-[-0.04em]"
  }
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
      className={`relative bg-bg-elevated border border-border-primary p-8 cursor-pointer transition-all hover:scale-[1.01] hover:border-accent/20 ${expanded ? "col-span-full" : ""} ${getCardTierClasses(pick.conviction_level)} ${getCardShadow(pick.conviction_level)} ${className}`}
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
      {pick.conviction_level === "exceptional" && (
        <>
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent rounded-t-lg" />
          <div className="absolute inset-0 rounded-lg pointer-events-none bg-[radial-gradient(ellipse_at_top_left,rgba(180,160,130,0.04),transparent_50%),radial-gradient(ellipse_at_bottom_right,rgba(26,122,90,0.03),transparent_50%)]" />
        </>
      )}
      <div className="flex items-center justify-between mb-3">
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
          {pick.opportunity_type && pick.opportunity_type !== "neither" && (
            <span
              className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                pick.opportunity_type === "compounder"
                  ? "bg-accent/10 text-accent"
                  : pick.opportunity_type === "mispricing"
                    ? "bg-purple-500/10 text-purple-400"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
              data-testid={`opportunity-type-${pick.ticker}`}
            >
              {pick.opportunity_type === "compounder"
                ? "Compounder"
                : pick.opportunity_type === "mispricing"
                  ? "Mispricing"
                  : "Both"}
            </span>
          )}
      </div>

      <p className="text-sm text-text-secondary mb-4 truncate">{pick.name}</p>

      <div className="flex items-center justify-between mb-6">
        <div>
          <span className={getScoreClasses(pick.conviction_level)}>
            {(pick.score || pick.composite_percentile).toFixed(0)}
          </span>
          <span className="block text-[11px] font-medium text-text-tertiary tracking-[0.15em] uppercase mt-1">
            conviction
          </span>
        </div>
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
          {pick.margin_of_safety != null && (
            <span className="text-text-secondary">
              MoS:{" "}
              <span className="text-bullish font-medium">
                {(pick.margin_of_safety * 100).toFixed(0)}%
              </span>
            </span>
          )}
        </div>
        <Sparkline
          bars={scoreData?.price_history}
          buyPrice={pick.buy_price}
          sellPrice={pick.sell_price}
        />
      </div>

      {(pick.max_position_pct != null || pick.timing_signal) && (
        <div className="flex items-center justify-between mb-4 text-sm">
          {pick.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-medium">
                {pick.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {pick.timing_signal && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                pick.timing_signal === "buy_now"
                  ? "bg-bullish/10 text-bullish"
                  : pick.timing_signal === "add_on_pullback"
                    ? "bg-accent/10 text-accent"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
              data-testid={`timing-signal-${pick.ticker}`}
            >
              {pick.timing_signal === "buy_now"
                ? "Buy now"
                : pick.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </div>
      )}

      <div className="space-y-2">
        {pick.winning_track === "compounder" ? (
          <>
            <PercentileBar value={pick.quality_percentile} label="Quality" />
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.momentum_percentile} label="Momentum" />
          </>
        ) : pick.winning_track === "mispricing" ? (
          <>
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.quality_percentile} label="Quality Floor" />
            <PercentileBar value={pick.momentum_percentile} label="Catalyst" />
          </>
        ) : (
          <>
            <PercentileBar value={pick.quality_percentile} label="Quality" />
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.momentum_percentile} label="Momentum" />
          </>
        )}
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
