"use client"

import { useState, useEffect } from "react"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import { getHoldings, getHoldingsHistory } from "@/lib/api/thirteenf"
import type {
  HoldingsResponse,
  HoldingsHistoryResponse,
  HolderResponse,
} from "@/lib/api/thirteenf"
import { ProGate } from "@/components/dashboard/pro-gate"

interface InstitutionalPositioningProps {
  ticker: string
}

/**
 * Convert a "YYYY-MM-DD" period_of_report into a quarter label like "Q4 2025".
 */
function periodToQuarter(period: string): string {
  if (!period) return ""
  const d = new Date(period + "T00:00:00")
  const month = d.getMonth() + 1
  const quarter = Math.ceil(month / 3)
  return `Q${quarter} ${d.getFullYear()}`
}

/**
 * Shorten a quarter period string for chart axis: "2025-12-31" -> "Q4 '25"
 */
function shortQuarterLabel(period: string): string {
  if (!period) return ""
  const d = new Date(period + "T00:00:00")
  const month = d.getMonth() + 1
  const quarter = Math.ceil(month / 3)
  const year = String(d.getFullYear()).slice(2)
  return `Q${quarter} '${year}`
}

function formatSharesChange(change: number): string {
  if (change === 0) return "0"
  const prefix = change > 0 ? "+" : ""
  return `${prefix}${change.toLocaleString()}`
}

function HolderRow({ holder }: { holder: HolderResponse }) {
  const changeColor =
    holder.shares_changed > 0
      ? "text-[var(--color-bullish)]"
      : holder.shares_changed < 0
        ? "text-[var(--color-bearish)]"
        : "text-text-tertiary"

  return (
    <tr className="border-b border-border-subtle last:border-b-0">
      <td className="py-2 pr-3 text-sm text-text-primary truncate max-w-[180px]">
        {holder.manager_name}
        {holder.is_new_position && (
          <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium">
            NEW
          </span>
        )}
      </td>
      <td className="py-2 px-3 text-sm font-mono text-text-secondary text-right">
        {holder.shares_held.toLocaleString()}
      </td>
      <td className={`py-2 px-3 text-sm font-mono text-right ${changeColor}`}>
        {formatSharesChange(holder.shares_changed)}
      </td>
      <td className="py-2 px-3 text-sm font-mono text-text-secondary text-right">
        {holder.pct_portfolio != null ? `${holder.pct_portfolio.toFixed(1)}%` : "\u2014"}
      </td>
      <td className="py-2 pl-3 text-sm font-mono text-text-tertiary text-right">
        {holder.quarters_held != null ? holder.quarters_held : "\u2014"}
      </td>
    </tr>
  )
}

function LoadingSkeleton() {
  return (
    <div data-testid="institutional-positioning-loading" className="space-y-3 animate-pulse">
      <div className="h-4 w-48 bg-white/[0.06] rounded" />
      <div className="grid grid-cols-3 gap-3">
        <div className="h-20 bg-white/[0.06] rounded-xl" />
        <div className="h-20 bg-white/[0.06] rounded-xl" />
        <div className="h-20 bg-white/[0.06] rounded-xl" />
      </div>
      <div className="h-40 bg-white/[0.06] rounded-xl" />
    </div>
  )
}

export function InstitutionalPositioning({ ticker }: InstitutionalPositioningProps) {
  const [holdings, setHoldings] = useState<HoldingsResponse | null>(null)
  const [history, setHistory] = useState<HoldingsHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showOtherHolders, setShowOtherHolders] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [holdingsRes, historyRes] = await Promise.all([
          getHoldings(ticker),
          getHoldingsHistory(ticker),
        ])
        if (!cancelled) {
          setHoldings(holdingsRes)
          setHistory(historyRes)
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load institutional data. Please try again later.")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [ticker])

  const isEmpty =
    !loading &&
    !error &&
    holdings != null &&
    holdings.summary.total_holders === 0 &&
    holdings.curated_holders.length === 0

  const periodLabel = holdings?.period_of_report
    ? periodToQuarter(holdings.period_of_report)
    : null

  const chartData =
    history?.quarters.map((q) => ({
      period: shortQuarterLabel(q.period),
      curated: q.curated_holders,
      total: q.total_holders,
    })) ?? []

  const netChange = holdings?.summary.net_shares_changed ?? 0

  return (
    <section data-testid="institutional-positioning" className="space-y-4">
      {loading && <LoadingSkeleton />}

      {error && (
        <div className="terminal-card p-6 text-center">
          <p className="text-sm text-text-secondary">{error}</p>
        </div>
      )}

      {isEmpty && (
        <div className="terminal-card p-6 text-center">
          <p className="text-sm text-text-secondary">
            No institutional holdings data available for {ticker}
          </p>
        </div>
      )}

      {!loading && !error && !isEmpty && holdings && (
        <>
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-text-primary">
              Institutional Positioning
            </h2>
            {periodLabel && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-accent/10 text-accent uppercase tracking-wider">
                {periodLabel}
              </span>
            )}
          </div>

          <p className="text-xs text-text-tertiary -mt-2">
            13F filings have a 45-day reporting lag from the period end date.
          </p>

          {/* Summary bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                Total Holders
              </span>
              <span className="text-2xl font-display text-text-primary block">
                {holdings.summary.total_holders}
              </span>
              <span className="text-xs text-text-tertiary">tracked institutions</span>
            </div>

            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                Curated Holders
              </span>
              <span className="text-2xl font-display text-text-primary block">
                {holdings.summary.curated_holders}
              </span>
              <span className="text-xs text-text-tertiary">high-conviction managers</span>
            </div>

            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                Net Accumulation
              </span>
              <div className="flex items-center gap-2">
                {netChange >= 0 ? (
                  <span
                    data-testid="net-accumulation-up"
                    className="text-2xl text-[var(--color-bullish)]"
                    aria-label="Accumulating"
                  >
                    &#9650;
                  </span>
                ) : (
                  <span
                    data-testid="net-accumulation-down"
                    className="text-2xl text-[var(--color-bearish)]"
                    aria-label="Distributing"
                  >
                    &#9660;
                  </span>
                )}
                <span
                  className={`text-lg font-mono ${
                    netChange >= 0
                      ? "text-[var(--color-bullish)]"
                      : "text-[var(--color-bearish)]"
                  }`}
                >
                  {formatSharesChange(netChange)}
                </span>
              </div>
              <span className="text-xs text-text-tertiary">net share change</span>
            </div>
          </div>

          {/* Gated detailed content: trend chart, holders table, other holders */}
          <ProGate>
            {/* Holder count trend chart */}
            {chartData.length > 1 && (
              <div className="terminal-card p-4 space-y-2">
                <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                  Holder Trend
                </span>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid-line)" />
                      <XAxis
                        dataKey="period"
                        tick={{ fontSize: 10 }}
                        stroke="var(--color-text-tertiary)"
                      />
                      <YAxis
                        tick={{ fontSize: 10 }}
                        stroke="var(--color-text-tertiary)"
                        allowDecimals={false}
                      />
                      <Tooltip />
                      <Area
                        type="monotone"
                        dataKey="curated"
                        stackId="1"
                        stroke="var(--color-accent)"
                        fill="var(--color-accent)"
                        fillOpacity={0.3}
                        name="Curated"
                      />
                      <Area
                        type="monotone"
                        dataKey="total"
                        stackId="2"
                        stroke="var(--color-text-tertiary)"
                        fill="var(--color-text-tertiary)"
                        fillOpacity={0.1}
                        name="Total"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Curated holders table */}
            {holdings.curated_holders.length > 0 && (
              <div className="terminal-card p-4 space-y-2">
                <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                  Curated Holders
                </span>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-border-subtle">
                        <th className="pb-2 pr-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium">
                          Fund
                        </th>
                        <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                          Shares
                        </th>
                        <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                          Change
                        </th>
                        <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                          % Portfolio
                        </th>
                        <th className="pb-2 pl-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                          Qtrs Held
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.curated_holders.map((holder) => (
                        <HolderRow key={holder.manager_name} holder={holder} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Expandable other holders */}
            {holdings.other_holders.length > 0 && (
              <div className="terminal-card overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowOtherHolders((prev) => !prev)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors"
                >
                  <span className="text-[11px] uppercase tracking-wider text-text-tertiary font-medium">
                    All Tracked Holders ({holdings.other_holders.length})
                  </span>
                  <span className="text-text-tertiary text-sm">
                    {showOtherHolders ? "\u25B2" : "\u25BC"}
                  </span>
                </button>
                {showOtherHolders && (
                  <div className="px-4 pb-4">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="border-b border-border-subtle">
                            <th className="pb-2 pr-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium">
                              Fund
                            </th>
                            <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                              Shares
                            </th>
                            <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                              Change
                            </th>
                            <th className="pb-2 px-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                              % Portfolio
                            </th>
                            <th className="pb-2 pl-3 text-[10px] uppercase tracking-wider text-text-tertiary font-medium text-right">
                              Qtrs Held
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {holdings.other_holders.map((holder) => (
                            <HolderRow key={holder.manager_name} holder={holder} />
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </ProGate>
        </>
      )}
    </section>
  )
}
