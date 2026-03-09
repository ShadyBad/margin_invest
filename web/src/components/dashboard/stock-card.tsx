"use client"

import { useState, useCallback } from "react"
import { motion } from "framer-motion"
import { ActionPill, Sparkline, PercentileBar, ConvictionBadge, AnimatedScore } from "@/components/ui"
import { ScoreDelta } from "@/components/ui/score-delta"
import { AssetPanel } from "./panel"
import { PanelErrorBoundary } from "./panel/panel-error-boundary"
import { getScore, getMetrics } from "@/lib/api/scores"
import { ApiError } from "@/lib/api/client"
import { getSectorColor } from "@/lib/sector-colors"
import Link from "next/link"
import type { PickSummary, ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"

function getCardTierClasses(convictionLevel: string): string {
  switch (convictionLevel) {
    case "exceptional":
      return "rounded-xl"
    case "high":
      return "rounded-xl"
    default:
      return "rounded-xl"
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
  rank?: number
}

export function StockCard({ pick, className = "", rank }: StockCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [scoreData, setScoreData] = useState<ScoreResponse | null>(null)
  const [metricsData, setMetricsData] = useState<InstitutionalMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDetails = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [scoreResult, metricsResult] = await Promise.allSettled([
        getScore(pick.ticker, ["price_history", "signal_history"]),
        getMetrics(pick.ticker),
      ])

      if (scoreResult.status === "fulfilled") {
        setScoreData(scoreResult.value)
      } else {
        const err = scoreResult.reason
        const requestId = err instanceof ApiError ? err.requestId : undefined
        if (requestId) console.error(`[${requestId}] Score fetch failed:`, err)
        setError("Unable to load candidate details")
        return
      }

      if (metricsResult.status === "fulfilled") {
        setMetricsData(metricsResult.value)
      } else {
        // Metrics failure is non-fatal — panel handles null metrics
        console.warn("Metrics fetch failed for", pick.ticker, metricsResult.reason)
        setMetricsData(null)
      }
    } finally {
      setLoading(false)
    }
  }, [pick.ticker])

  const handleClick = useCallback(async () => {
    if (expanded) {
      setExpanded(false)
      return
    }

    setExpanded(true)

    if (!scoreData) {
      await fetchDetails()
    }
  }, [expanded, scoreData, fetchDetails])

  return (
    <>
    <div
      className={`relative bg-bg-elevated border border-border-primary border-l-2 cursor-pointer hover:border-[var(--color-accent-medium)] hover:shadow-card-hover p-6 ${getCardTierClasses(pick.composite_tier)} ${getCardShadow(pick.composite_tier)} ${className}`}
      style={{
        borderLeftColor: getSectorColor(pick.sector),
        transition: `box-shadow 150ms var(--ease-out-expo), border-color 150ms var(--ease-out-expo)`,
      }}
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
      {pick.composite_tier === "exceptional" && (
        <div className="absolute inset-0 rounded-xl pointer-events-none bg-[radial-gradient(ellipse_at_top_left,rgba(180,160,130,0.04),transparent_50%),radial-gradient(ellipse_at_bottom_right,rgba(26,122,90,0.03),transparent_50%)]" />
      )}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {rank != null && rank <= 3 && (
            <span
              className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold"
              style={{
                background: rank === 1
                  ? 'var(--color-accent)'
                  : 'var(--color-border-subtle)',
                color: rank === 1
                  ? 'var(--color-bg-primary)'
                  : 'var(--color-text-secondary)',
              }}
            >
              {rank}
            </span>
          )}
          <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
          <Link
            href={`/asset/${pick.ticker}`}
            className="text-xs text-text-tertiary hover:text-accent transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Full report &rarr;
          </Link>
          {pick.data_freshness === "expired" && (
            <span
              className="text-xs px-1.5 py-0.5 rounded bg-danger/10 text-danger"
              data-testid={`freshness-${pick.ticker}`}
            >
              Expired
            </span>
          )}
        </div>
        <motion.div
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 15 }}
        >
          <ConvictionBadge level={pick.composite_tier} />
        </motion.div>
          {pick.ml_override === "promoted" && (
            <span
              className="text-xs text-bullish font-semibold"
              data-testid={`ml-override-${pick.ticker}`}
              title="ML-promoted"
            >
              ▲
            </span>
          )}
          {pick.ml_override === "demoted" && (
            <span
              className="text-xs text-bearish font-semibold"
              data-testid={`ml-override-${pick.ticker}`}
              title="ML-demoted"
            >
              ▼
            </span>
          )}
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

      <p className="text-sm text-text-secondary mb-4 line-clamp-2">{pick.name}</p>

      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-end gap-2">
            <AnimatedScore
              value={pick.score ?? pick.composite_percentile}
              className={getScoreClasses(pick.composite_tier)}
            />
            <ScoreDelta
              current={pick.score ?? pick.composite_percentile}
              previous={pick.previous_score ?? null}
            />
          </div>
          <span className="block text-xs font-medium text-text-tertiary tracking-[0.15em] uppercase mt-1">
            composite
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
            <span className={`font-medium ${pick.sell_price != null ? "text-text-primary" : "text-text-tertiary"}`}>
              {pick.sell_price != null
                ? `$${pick.sell_price.toFixed(2)}`
                : pick.price_target_invalid_reason === "insufficient_data"
                  ? "Needs data"
                  : pick.price_target_invalid_reason === "single_method"
                    ? "Low confidence"
                    : pick.price_target_invalid_reason === "low_agreement"
                      ? "Methods diverge"
                      : pick.price_target_invalid_reason
                        ? "Unavailable"
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
              <span
                className="font-medium"
                style={{
                  color: pick.margin_of_safety >= 1
                    ? 'var(--color-accent)'
                    : 'var(--color-bullish)',
                }}
              >
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
          <div className="text-center py-4">
            <p className="text-sm font-medium text-text-primary mb-1">
              Unable to load candidate details
            </p>
            <p className="text-xs text-text-secondary mb-3">
              This data is temporarily unavailable.
            </p>
            <button
              type="button"
              className="text-xs text-accent hover:text-accent/80 underline underline-offset-2"
              onClick={(e) => {
                e.stopPropagation()
                setScoreData(null)
                fetchDetails()
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )}
    </div>
    {scoreData && (
      <PanelErrorBoundary onDismiss={() => setExpanded(false)}>
        <AssetPanel
          isOpen={expanded && !loading}
          onClose={() => setExpanded(false)}
          ticker={pick.ticker}
          scoredResult={scoreData}
          metrics={metricsData}
        />
      </PanelErrorBoundary>
    )}
    </>
  )
}
