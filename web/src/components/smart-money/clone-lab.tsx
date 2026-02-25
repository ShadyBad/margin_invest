"use client"

import { useState, useEffect, useCallback } from "react"
import { getManagers, getClonePortfolio } from "@/lib/api/thirteenf"
import type { ManagerResponse, CloneResponse } from "@/lib/api/thirteenf"

const STRATEGIES = [
  { id: "equal_weight_top_10", label: "Equal-weight top 10" },
  { id: "equal_weight_top_20", label: "Equal-weight top 20" },
  { id: "market_cap_weighted", label: "Market-cap weighted" },
] as const

type StrategyId = (typeof STRATEGIES)[number]["id"]

export function CloneLab() {
  const [managers, setManagers] = useState<ManagerResponse[]>([])
  const [managersLoading, setManagersLoading] = useState(true)
  const [selectedManagerId, setSelectedManagerId] = useState<number | null>(null)
  const [strategy, setStrategy] = useState<StrategyId>("equal_weight_top_10")
  const [clone, setClone] = useState<CloneResponse | null>(null)
  const [cloneLoading, setCloneLoading] = useState(false)

  // Load curated managers on mount
  useEffect(() => {
    let cancelled = false

    async function load() {
      setManagersLoading(true)
      try {
        const data = await getManagers("curated")
        if (!cancelled) setManagers(data)
      } catch {
        // leave empty
      } finally {
        if (!cancelled) setManagersLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  // Fetch clone portfolio when manager or strategy changes
  const fetchClone = useCallback(
    async (managerId: number, strat: StrategyId) => {
      setCloneLoading(true)
      setClone(null)
      try {
        const data = await getClonePortfolio(managerId, strat)
        setClone(data)
      } catch {
        // leave null
      } finally {
        setCloneLoading(false)
      }
    },
    [],
  )

  function handleManagerChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    if (!val) {
      setSelectedManagerId(null)
      setClone(null)
      return
    }
    const id = Number(val)
    setSelectedManagerId(id)
    fetchClone(id, strategy)
  }

  function handleStrategyChange(strat: StrategyId) {
    setStrategy(strat)
    if (selectedManagerId != null) {
      fetchClone(selectedManagerId, strat)
    }
  }

  const maxWeight =
    clone && clone.positions.length > 0
      ? Math.max(...clone.positions.map((p) => p.target_weight))
      : 1

  const perf = clone?.historical_performance

  return (
    <div data-testid="clone-lab" className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Manager selector */}
        <div className="flex-1">
          <label
            htmlFor="manager-select"
            className="block text-[10px] uppercase tracking-wider text-text-tertiary font-medium mb-1"
          >
            Manager
          </label>
          <select
            id="manager-select"
            data-testid="manager-select"
            className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
            value={selectedManagerId ?? ""}
            onChange={handleManagerChange}
            disabled={managersLoading}
          >
            <option value="">Select a manager...</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {/* Strategy selector */}
        <div>
          <span className="block text-[10px] uppercase tracking-wider text-text-tertiary font-medium mb-1">
            Strategy
          </span>
          <div className="flex gap-2">
            {STRATEGIES.map((s) => (
              <label key={s.id} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="clone-strategy"
                  value={s.id}
                  checked={strategy === s.id}
                  onChange={() => handleStrategyChange(s.id)}
                  className="accent-accent"
                />
                <span
                  className={`text-xs ${
                    strategy === s.id ? "text-text-primary" : "text-text-tertiary"
                  }`}
                >
                  {s.label}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Empty state */}
      {!selectedManagerId && !cloneLoading && (
        <div className="terminal-card p-8 text-center">
          <p className="text-sm text-text-secondary">
            Select a manager to generate a clone portfolio
          </p>
        </div>
      )}

      {/* Loading */}
      {cloneLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 w-40 bg-white/[0.06] rounded" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-white/[0.06] rounded-xl" />
          ))}
        </div>
      )}

      {/* Portfolio allocation table */}
      {!cloneLoading && clone && (
        <div className="space-y-6">
          <section>
            <h3 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wider">
              Portfolio Allocation
            </h3>
            <div className="terminal-card overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-2 text-[10px] uppercase tracking-wider text-text-tertiary font-medium">
                      Ticker
                    </th>
                    <th className="px-4 py-2 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right w-24">
                      Weight
                    </th>
                    <th className="px-4 py-2 text-[10px] uppercase tracking-wider text-text-tertiary font-medium w-1/3">
                      Allocation
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {clone.positions.map((pos) => (
                    <tr
                      key={pos.ticker}
                      className="border-b border-border-subtle last:border-b-0"
                    >
                      <td className="px-4 py-2.5 text-sm font-mono text-text-primary font-medium">
                        {pos.ticker}
                      </td>
                      <td className="px-4 py-2.5 text-sm font-mono text-text-secondary text-right">
                        {(pos.target_weight * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent rounded-full transition-all"
                            style={{
                              width: `${(pos.target_weight / maxWeight) * 100}%`,
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Historical performance */}
          <section>
            <h3 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wider">
              Historical Performance
            </h3>
            {perf ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="terminal-card p-4 space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-text-tertiary">
                    1Y Return
                  </span>
                  <span
                    className={`text-lg font-mono block ${
                      perf.return_1y != null && perf.return_1y >= 0
                        ? "text-[var(--color-bullish)]"
                        : "text-[var(--color-bearish)]"
                    }`}
                  >
                    {perf.return_1y != null
                      ? `${(perf.return_1y * 100).toFixed(1)}%`
                      : "\u2014"}
                  </span>
                </div>
                <div className="terminal-card p-4 space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-text-tertiary">
                    3Y CAGR
                  </span>
                  <span
                    className={`text-lg font-mono block ${
                      perf.cagr_3y != null && perf.cagr_3y >= 0
                        ? "text-[var(--color-bullish)]"
                        : "text-[var(--color-bearish)]"
                    }`}
                  >
                    {perf.cagr_3y != null
                      ? `${(perf.cagr_3y * 100).toFixed(1)}%`
                      : "\u2014"}
                  </span>
                </div>
                <div className="terminal-card p-4 space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-text-tertiary">
                    Max Drawdown
                  </span>
                  <span className="text-lg font-mono text-[var(--color-bearish)] block">
                    {perf.max_drawdown != null
                      ? `${(perf.max_drawdown * 100).toFixed(1)}%`
                      : "\u2014"}
                  </span>
                </div>
                <div className="terminal-card p-4 space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-text-tertiary">
                    Sharpe
                  </span>
                  <span className="text-lg font-mono text-text-primary block">
                    {perf.sharpe != null ? perf.sharpe.toFixed(2) : "\u2014"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="terminal-card p-6 text-center">
                <p className="text-sm text-text-tertiary">
                  Performance data not yet available
                </p>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Disclaimer footer — always visible */}
      <div data-testid="clone-disclaimer" className="terminal-card p-3">
        <p className="text-xs text-text-tertiary text-center">
          Clone portfolios are based on 13F filings which have a 45-day reporting lag.
          Past performance is not indicative of future results. This is not investment advice.
        </p>
      </div>
    </div>
  )
}
