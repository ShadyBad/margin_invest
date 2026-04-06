"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { getWatchlist, removeFromWatchlist } from "@/lib/api/watchlist"
import { getSectorColor } from "@/lib/sector-colors"
import { formatScore } from "@/lib/format"
import type { UserWatchlistItem } from "@/lib/api/types"

export function UserWatchlist() {
  const [items, setItems] = useState<UserWatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getWatchlist()
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load watchlist")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  async function handleRemove(ticker: string) {
    // Optimistic update
    setItems((prev) => prev.filter((i) => i.ticker !== ticker))
    try {
      await removeFromWatchlist(ticker)
    } catch {
      // If removal fails, re-fetch to restore state
      getWatchlist()
        .then((res) => setItems(res.items))
        .catch(() => {/* best-effort */})
    }
  }

  if (loading) {
    return (
      <div className="space-y-2" data-testid="user-watchlist-skeleton">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-12 rounded-lg bg-bg-elevated animate-pulse border border-border-subtle"
          />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-text-secondary" data-testid="user-watchlist-error">
        {error}
      </p>
    )
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-elevated p-6 text-center" data-testid="user-watchlist-empty">
        <p className="text-sm text-text-secondary mb-2">
          No tickers on your watchlist yet.
        </p>
        <Link
          href="/explore"
          className="text-sm text-accent-primary hover:underline underline-offset-2"
        >
          Explore stocks to add
        </Link>
      </div>
    )
  }

  return (
    <div
      className="rounded-lg border border-border-subtle bg-bg-elevated overflow-hidden"
      data-testid="user-watchlist"
    >
      {items.map((item) => (
        <div
          key={item.ticker}
          className="flex items-center gap-4 px-4 py-3 border-b border-border-subtle last:border-b-0"
          data-testid={`watchlist-item-${item.ticker}`}
        >
          {/* Sector dot */}
          <span
            className="h-2 w-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: getSectorColor(item.sector) }}
            title={item.sector ?? "Unknown sector"}
          />

          {/* Ticker link + name */}
          <div className="flex-1 min-w-0">
            <Link
              href={`/asset/${item.ticker}`}
              className="text-sm font-bold text-text-primary hover:text-accent-primary transition-colors"
            >
              {item.ticker}
            </Link>
            {item.name && (
              <span className="text-sm text-text-secondary ml-2 truncate">
                {item.name}
              </span>
            )}
          </div>

          {/* Sector badge */}
          {item.sector && (
            <span
              className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-xs text-text-secondary border border-border-subtle"
              style={{ borderColor: getSectorColor(item.sector) }}
            >
              {item.sector}
            </span>
          )}

          {/* Composite score */}
          <span className="text-sm font-mono text-text-primary w-10 text-right flex-shrink-0">
            {formatScore(item.composite_score)}
          </span>

          {/* Remove button */}
          <button
            type="button"
            onClick={() => handleRemove(item.ticker)}
            aria-label={`Remove ${item.ticker}`}
            className="text-xs text-text-tertiary hover:text-bearish transition-colors flex-shrink-0 px-2 py-1 rounded border border-transparent hover:border-border-subtle"
          >
            Remove
          </button>
        </div>
      ))}
    </div>
  )
}
