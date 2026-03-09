"use client"

import { useState, useEffect } from "react"
import { getOverlap, getNewPositions } from "@/lib/api/thirteenf"
import type {
  OverlapResponse,
  NewPositionResponse,
} from "@/lib/api/thirteenf"

function LoadingSkeleton() {
  return (
    <div data-testid="market-signals-loading" className="space-y-6 animate-pulse">
      <div className="h-4 w-48 bg-white/[0.06] rounded" />
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 bg-white/[0.06] rounded-xl" />
        ))}
      </div>
      <div className="h-4 w-40 bg-white/[0.06] rounded" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-24 bg-white/[0.06] rounded-xl" />
        <div className="h-24 bg-white/[0.06] rounded-xl" />
      </div>
    </div>
  )
}

export function MarketSignals() {
  const [overlap, setOverlap] = useState<OverlapResponse | null>(null)
  const [newPositions, setNewPositions] = useState<NewPositionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(false)
      try {
        const [overlapData, newPosData] = await Promise.all([
          getOverlap(),
          getNewPositions(),
        ])
        if (!cancelled) {
          setOverlap(overlapData)
          setNewPositions(newPosData)
        }
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <LoadingSkeleton />

  if (error || (!overlap && !newPositions)) {
    return (
      <div className="terminal-card p-8 text-center">
        <p className="text-sm text-text-secondary">No market signals data available</p>
      </div>
    )
  }

  const maxHolderCount =
    overlap && overlap.most_held.length > 0
      ? Math.max(...overlap.most_held.map((e) => e.holder_count))
      : 1

  return (
    <div data-testid="market-signals" className="space-y-8">
      {/* Section 1: Most Held Positions */}
      {overlap && overlap.most_held.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wider">
            Most Held Positions
          </h3>
          <div className="terminal-card overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium">
                    Ticker
                  </th>
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                    Total Holders
                  </th>
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                    Curated
                  </th>
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium w-1/3">
                    Concentration
                  </th>
                </tr>
              </thead>
              <tbody>
                {overlap.most_held.map((entry) => (
                  <tr
                    key={entry.ticker}
                    className="border-b border-border-subtle last:border-b-0"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono text-text-primary font-medium">
                      {entry.ticker}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-text-secondary text-right">
                      {entry.holder_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-accent text-right">
                      {entry.curated_count}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent rounded-full transition-all"
                            style={{
                              width: `${(entry.curated_count / maxHolderCount) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Section 2: New Position Alerts */}
      <section>
        <h3 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wider">
          New Position Alerts
        </h3>
        {newPositions && newPositions.new_positions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {newPositions.new_positions.map((pos) => (
              <div key={pos.ticker} className="terminal-card p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-lg font-mono font-semibold text-text-primary">
                    {pos.ticker}
                  </span>
                  <span className="text-xs font-mono text-text-secondary">
                    ${pos.total_value_millions.toFixed(1)}M
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {pos.managers.map((name) => (
                    <span
                      key={name}
                      className="text-xs px-1.5 py-0.5 rounded bg-accent/10 text-accent"
                    >
                      {name}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-3 text-xs text-text-tertiary">
                  <span>{pos.total_new_funds} funds adding</span>
                  <span>{pos.curated_new_funds} curated</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="terminal-card p-6 text-center">
            <p className="text-sm text-text-tertiary">
              No data available for this quarter
            </p>
          </div>
        )}
      </section>

      {/* Section 3: Crowded Trades */}
      <section>
        <h3 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wider">
          Crowded Trades
        </h3>
        {overlap && overlap.crowded_trades.length > 0 ? (
          <div className="terminal-card overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium">
                    Ticker
                  </th>
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                    New Positions
                  </th>
                  <th className="px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                    % Funds Adding
                  </th>
                </tr>
              </thead>
              <tbody>
                {overlap.crowded_trades.map((trade) => (
                  <tr
                    key={trade.ticker}
                    className="border-b border-border-subtle last:border-b-0"
                  >
                    <td className="px-4 py-2.5 text-sm font-mono text-text-primary font-medium">
                      {trade.ticker}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-text-secondary text-right">
                      {trade.new_position_count}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-warning text-right">
                      {(trade.pct_funds_adding * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div
            data-testid="crowded-trades-empty"
            className="terminal-card p-6 text-center"
          >
            <p className="text-sm text-text-tertiary">
              No crowded trades detected this quarter
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
