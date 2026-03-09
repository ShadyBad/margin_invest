"use client"

import { useState, useEffect } from "react"
import { getManagers, getManagerPortfolio } from "@/lib/api/thirteenf"
import type { ManagerResponse, ManagerPortfolioResponse } from "@/lib/api/thirteenf"

function LoadingSkeleton() {
  return (
    <div data-testid="fund-tracker-loading" className="space-y-3 animate-pulse">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-16 bg-white/[0.06] rounded-xl"
        />
      ))}
    </div>
  )
}

function PortfolioDetail({ portfolio }: { portfolio: ManagerPortfolioResponse }) {
  const { holdings, changes_summary } = portfolio

  return (
    <div className="px-4 pb-4 space-y-4">
      {/* Position table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border-subtle">
              <th className="pb-2 pr-3 text-xs uppercase tracking-wider text-text-tertiary font-medium">
                Ticker
              </th>
              <th className="pb-2 px-3 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                Shares
              </th>
              <th className="pb-2 px-3 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                Value ($M)
              </th>
              <th className="pb-2 px-3 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                % Portfolio
              </th>
              <th className="pb-2 pl-3 text-xs uppercase tracking-wider text-text-tertiary font-medium text-right">
                Change
              </th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const changeColor =
                h.shares_changed > 0
                  ? "text-[var(--color-bullish)]"
                  : h.shares_changed < 0
                    ? "text-[var(--color-bearish)]"
                    : "text-text-tertiary"
              const changePrefix = h.shares_changed > 0 ? "+" : ""
              return (
                <tr
                  key={h.cusip}
                  className="border-b border-border-subtle last:border-b-0"
                >
                  <td className="py-2 pr-3 text-sm text-text-primary font-medium">
                    {h.ticker ?? h.cusip}
                    {h.is_new_position && (
                      <span className="ml-1.5 text-xs px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium">
                        NEW
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-sm font-mono text-text-secondary text-right">
                    {h.shares_held.toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-sm font-mono text-text-secondary text-right">
                    ${h.value_millions.toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-sm font-mono text-text-secondary text-right">
                    {h.pct_portfolio.toFixed(1)}%
                  </td>
                  <td className={`py-2 pl-3 text-sm font-mono text-right ${changeColor}`}>
                    {changePrefix}{h.shares_changed.toLocaleString()}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Changes summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="terminal-card p-3 space-y-1">
          <span className="text-xs uppercase tracking-wider text-text-tertiary">
            New Positions
          </span>
          <div className="flex flex-wrap gap-1">
            {changes_summary.new_positions.length > 0 ? (
              changes_summary.new_positions.map((t) => (
                <span
                  key={t}
                  className="text-xs px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono"
                >
                  {t}
                </span>
              ))
            ) : (
              <span className="text-xs text-text-tertiary">None</span>
            )}
          </div>
        </div>
        <div className="terminal-card p-3 space-y-1">
          <span className="text-xs uppercase tracking-wider text-text-tertiary">
            Exited Positions
          </span>
          <div className="flex flex-wrap gap-1">
            {changes_summary.exited_positions.length > 0 ? (
              changes_summary.exited_positions.map((t) => (
                <span
                  key={t}
                  className="text-xs px-1.5 py-0.5 rounded bg-bearish/10 text-bearish font-mono"
                >
                  {t}
                </span>
              ))
            ) : (
              <span className="text-xs text-text-tertiary">None</span>
            )}
          </div>
        </div>
        <div className="terminal-card p-3 space-y-1">
          <span className="text-xs uppercase tracking-wider text-text-tertiary">
            Increased
          </span>
          <span className="text-lg font-mono text-[var(--color-bullish)] block">
            {changes_summary.increased}
          </span>
        </div>
        <div className="terminal-card p-3 space-y-1">
          <span className="text-xs uppercase tracking-wider text-text-tertiary">
            Decreased
          </span>
          <span className="text-lg font-mono text-[var(--color-bearish)] block">
            {changes_summary.decreased}
          </span>
        </div>
      </div>
    </div>
  )
}

export function FundTracker() {
  const [managers, setManagers] = useState<ManagerResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)
  const [portfolio, setPortfolio] = useState<ManagerPortfolioResponse | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const data = await getManagers()
        if (!cancelled) setManagers(data)
      } catch {
        // handled by empty state
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleRowClick(id: number) {
    if (expandedId === id) {
      setExpandedId(null)
      setPortfolio(null)
      return
    }

    setExpandedId(id)
    setPortfolioLoading(true)
    setPortfolio(null)

    try {
      const data = await getManagerPortfolio(id)
      setPortfolio(data)
    } catch {
      // leave portfolio null
    } finally {
      setPortfolioLoading(false)
    }
  }

  if (loading) return <LoadingSkeleton />

  if (managers.length === 0) {
    return (
      <div className="terminal-card p-8 text-center">
        <p className="text-sm text-text-secondary">No manager data available</p>
      </div>
    )
  }

  return (
    <div data-testid="fund-tracker" className="space-y-1">
      {/* Table header */}
      <div className="grid grid-cols-[1fr_100px_120px_80px_auto] gap-3 px-4 py-2 text-xs uppercase tracking-wider text-text-tertiary font-medium">
        <span>Manager</span>
        <span>Tier</span>
        <span className="text-right">AUM</span>
        <span className="text-right">Holdings</span>
        <span>Top Positions</span>
      </div>

      {/* Manager rows */}
      {managers.map((m) => (
        <div key={m.id}>
          <button
            data-testid={`manager-row-${m.id}`}
            type="button"
            onClick={() => handleRowClick(m.id)}
            className={`w-full grid grid-cols-[1fr_100px_120px_80px_auto] gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors rounded-lg ${
              expandedId === m.id ? "bg-white/[0.03]" : ""
            }`}
          >
            <span className="text-sm text-text-primary font-medium truncate">
              {m.name}
            </span>
            <span>
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                m.tier === "curated"
                  ? "bg-accent/10 text-accent"
                  : "bg-white/[0.06] text-text-secondary"
              }`}>
                {m.tier}
              </span>
            </span>
            <span className="text-sm font-mono text-text-secondary text-right">
              {m.aum_millions != null ? `$${m.aum_millions.toLocaleString()}M` : "\u2014"}
            </span>
            <span className="text-sm font-mono text-text-secondary text-right">
              {m.total_holdings}
            </span>
            <div className="flex flex-wrap gap-1">
              {m.top_positions.slice(0, 5).map((ticker) => (
                <span
                  key={ticker}
                  className="text-xs px-1.5 py-0.5 rounded bg-white/[0.06] text-text-secondary font-mono"
                >
                  {ticker}
                </span>
              ))}
            </div>
          </button>

          {/* Expanded portfolio detail */}
          {expandedId === m.id && (
            <div className="terminal-card mt-1 mb-2 overflow-hidden">
              {portfolioLoading && (
                <div className="p-4 animate-pulse">
                  <div className="h-4 w-32 bg-white/[0.06] rounded mb-2" />
                  <div className="h-32 bg-white/[0.06] rounded" />
                </div>
              )}
              {!portfolioLoading && portfolio && (
                <PortfolioDetail portfolio={portfolio} />
              )}
              {!portfolioLoading && !portfolio && (
                <div className="p-4 text-sm text-text-tertiary">
                  Unable to load portfolio data
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
