"use client"

import { useState } from "react"
import { addToWatchlist, removeFromWatchlist } from "@/lib/api/watchlist"

interface WatchlistButtonProps {
  ticker: string
  isOnWatchlist: boolean
}

export function WatchlistButton({ ticker, isOnWatchlist }: WatchlistButtonProps) {
  const [onWatchlist, setOnWatchlist] = useState(isOnWatchlist)
  const [loading, setLoading] = useState(false)

  async function handleClick() {
    if (loading) return
    setLoading(true)
    try {
      if (onWatchlist) {
        await removeFromWatchlist(ticker)
        setOnWatchlist(false)
      } else {
        await addToWatchlist(ticker)
        setOnWatchlist(true)
      }
    } catch {
      // Silently fail — state remains unchanged
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      className={[
        "inline-flex items-center gap-2 px-4 py-2 rounded border text-sm font-medium transition-colors disabled:opacity-50",
        onWatchlist
          ? "border-accent-primary text-accent-primary bg-accent-primary/10 hover:bg-accent-primary/20"
          : "border-border-subtle text-text-secondary hover:text-text-primary hover:border-accent-primary",
      ].join(" ")}
      data-testid="watchlist-button"
    >
      {/* Star icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill={onWatchlist ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>

      {onWatchlist ? "On Watchlist" : "Add to Watchlist"}
    </button>
  )
}
