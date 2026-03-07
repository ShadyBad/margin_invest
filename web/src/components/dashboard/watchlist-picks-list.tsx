"use client"

import { useState, useCallback } from "react"
import { motion } from "framer-motion"
import { ConvictionBadge } from "@/components/ui"
import { AssetPanel } from "./panel"
import { PanelErrorBoundary } from "./panel/panel-error-boundary"
import { getScore, getMetrics } from "@/lib/api/scores"
import { ApiError } from "@/lib/api/client"
import { getSectorColor } from "@/lib/sector-colors"
import type { WatchlistItem, ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"

interface WatchlistPicksListProps {
  items: WatchlistItem[]
  className?: string
}

function WatchlistRow({ item }: { item: WatchlistItem }) {
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
        getScore(item.ticker, ["price_history", "signal_history"]),
        getMetrics(item.ticker),
      ])

      if (scoreResult.status === "fulfilled") {
        setScoreData(scoreResult.value)
      } else {
        const err = scoreResult.reason
        const requestId = err instanceof ApiError ? err.requestId : undefined
        if (requestId) console.error(`[${requestId}] Score fetch failed:`, err)
        setError("Unable to load details")
        return
      }

      if (metricsResult.status === "fulfilled") {
        setMetricsData(metricsResult.value)
      } else {
        setMetricsData(null)
      }
    } finally {
      setLoading(false)
    }
  }, [item.ticker])

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

  const sectorColor = getSectorColor(item.sector)

  return (
    <>
      <div
        className="flex items-center gap-4 px-5 py-3.5 cursor-pointer transition-colors hover:bg-bg-primary/50 border-b border-border-primary last:border-b-0"
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
        data-testid={`watchlist-row-${item.ticker}`}
      >
        {/* Sector dot */}
        <span
          className="h-2 w-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: sectorColor }}
          title={item.sector ?? "Unknown sector"}
        />

        {/* Ticker + name */}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-bold text-text-primary">{item.ticker}</span>
          <span className="text-sm text-text-secondary ml-2 truncate">{item.name}</span>
        </div>

        {/* Conviction badge */}
        <ConvictionBadge level={item.composite_tier} />

        {/* Score */}
        <span className="text-sm font-mono text-text-primary w-8 text-right">
          {Math.round(item.composite_raw_score)}
        </span>

        {/* Price + upside */}
        <div className="text-sm text-right w-28 flex-shrink-0">
          {item.actual_price != null && (
            <span className="text-text-secondary">
              ${item.actual_price.toFixed(2)}
            </span>
          )}
          {item.price_upside != null && (
            <span className={`ml-1.5 ${item.price_upside >= 0 ? "text-bullish" : "text-bearish"}`}>
              {item.price_upside >= 0 ? "+" : ""}
              {(item.price_upside * 100).toFixed(1)}%
            </span>
          )}
        </div>

        {/* Chevron */}
        <motion.svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-text-tertiary flex-shrink-0"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </motion.svg>
      </div>

      {/* Loading state */}
      {expanded && loading && (
        <div className="px-5 py-4 flex items-center justify-center border-b border-border-primary">
          <div className="animate-spin h-5 w-5 border-2 border-accent border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-text-secondary">Loading details...</span>
        </div>
      )}

      {/* Error state */}
      {expanded && error && (
        <div className="px-5 py-4 border-b border-border-primary">
          <div className="text-center">
            <p className="text-sm text-text-secondary mb-2">{error}</p>
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

      {/* AssetPanel overlay */}
      {scoreData && (
        <PanelErrorBoundary onDismiss={() => setExpanded(false)}>
          <AssetPanel
            isOpen={expanded && !loading}
            onClose={() => setExpanded(false)}
            ticker={item.ticker}
            scoredResult={scoreData}
            metrics={metricsData}
          />
        </PanelErrorBoundary>
      )}
    </>
  )
}

export function WatchlistPicksList({ items, className = "" }: WatchlistPicksListProps) {
  const [search, setSearch] = useState("")

  if (items.length === 0) {
    return (
      <p className="text-sm text-text-secondary" data-testid="watchlist-empty">
        No Watchlist Picks available
      </p>
    )
  }

  const filtered = search
    ? items.filter(
        (item) =>
          item.ticker.toLowerCase().includes(search.toLowerCase()) ||
          item.name.toLowerCase().includes(search.toLowerCase()),
      )
    : items

  return (
    <div
      className={`bg-bg-elevated border border-border-primary rounded-sm overflow-hidden ${className}`}
      data-testid="watchlist-picks-list"
    >
      {/* Search bar */}
      {items.length > 10 && (
        <div className="px-5 py-2.5 border-b border-border-primary">
          <input
            type="text"
            placeholder="Search ticker or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none"
            data-testid="watchlist-search"
          />
        </div>
      )}

      {/* Column headers */}
      <div className="flex items-center gap-4 px-5 py-2 text-[10px] font-mono uppercase tracking-[0.15em] text-text-tertiary border-b border-border-primary sticky top-0 bg-bg-elevated z-10">
        <span className="w-2" />
        <span className="flex-1">Ticker / Name</span>
        <span>Tier</span>
        <span className="w-8 text-right">Score</span>
        <span className="w-28 text-right">Price / Upside</span>
        <span className="w-4" />
      </div>

      {filtered.map((item) => (
        <WatchlistRow key={item.ticker} item={item} />
      ))}

      {search && filtered.length === 0 && (
        <div className="px-5 py-8 text-center text-sm text-text-tertiary">
          No matches for &ldquo;{search}&rdquo;
        </div>
      )}
    </div>
  )
}
