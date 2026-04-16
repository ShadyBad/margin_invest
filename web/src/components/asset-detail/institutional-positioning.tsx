"use client"

import { useState, useEffect } from "react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
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

function HolderRow({ holder, idx }: { holder: HolderResponse; idx: number }) {
  const changeColor =
    holder.shares_changed > 0
      ? "var(--color-bullish)"
      : holder.shares_changed < 0
        ? "var(--color-bearish)"
        : "var(--color-text-tertiary)"

  return (
    <tr
      style={{
        background: idx % 2 === 0 ? "var(--color-surface)" : "var(--color-surface-container-lowest)",
      }}
    >
      <td className="py-2 pr-3 text-sm truncate max-w-[180px]" style={{ color: "var(--color-on-surface)" }}>
        {holder.manager_name}
        {holder.is_new_position && (
          <span
            className="ml-1.5 text-xs px-1.5 py-0.5 rounded-sm font-medium"
            style={{
              background: "color-mix(in srgb, var(--color-primary-muted) 10%, transparent)",
              color: "var(--color-primary-muted)",
            }}
          >
            NEW
          </span>
        )}
      </td>
      <td className="py-2 px-3 text-sm text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
        {holder.shares_held.toLocaleString()}
      </td>
      <td className="py-2 px-3 text-sm text-right" style={{ fontFamily: "var(--font-data)", color: changeColor }}>
        {formatSharesChange(holder.shares_changed)}
      </td>
      <td className="py-2 px-3 text-sm text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
        {holder.pct_portfolio != null ? `${holder.pct_portfolio.toFixed(1)}%` : "\u2014"}
      </td>
      <td className="py-2 pl-3 text-sm text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
        {holder.quarters_held != null ? holder.quarters_held : "\u2014"}
      </td>
    </tr>
  )
}

function LoadingSkeleton() {
  return (
    <div data-testid="institutional-positioning-loading" className="space-y-3 animate-pulse">
      <div className="h-4 w-48 rounded" style={{ background: "var(--color-surface-container)" }} />
      <div className="grid grid-cols-3 gap-3">
        <div className="h-20 rounded-lg" style={{ background: "var(--color-surface-container)" }} />
        <div className="h-20 rounded-lg" style={{ background: "var(--color-surface-container)" }} />
        <div className="h-20 rounded-lg" style={{ background: "var(--color-surface-container)" }} />
      </div>
      <div className="h-40 rounded-lg" style={{ background: "var(--color-surface-container)" }} />
    </div>
  )
}

function HolderTable({ holders, label }: { holders: HolderResponse[]; label: string }) {
  return (
    <div className="space-y-2">
      <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
        {label}
      </span>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="pb-2 pr-3 text-label-sm font-medium" style={{ color: "var(--color-text-tertiary)" }}>
                Fund
              </th>
              <th className="pb-2 px-3 text-label-sm font-medium text-right" style={{ color: "var(--color-text-tertiary)" }}>
                Shares
              </th>
              <th className="pb-2 px-3 text-label-sm font-medium text-right" style={{ color: "var(--color-text-tertiary)" }}>
                Change
              </th>
              <th className="pb-2 px-3 text-label-sm font-medium text-right" style={{ color: "var(--color-text-tertiary)" }}>
                % Portfolio
              </th>
              <th className="pb-2 pl-3 text-label-sm font-medium text-right" style={{ color: "var(--color-text-tertiary)" }}>
                Qtrs Held
              </th>
            </tr>
          </thead>
          <tbody>
            {holders.map((holder, idx) => (
              <HolderRow key={holder.manager_name} holder={holder} idx={idx} />
            ))}
          </tbody>
        </table>
      </div>
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
    <section
      data-testid="institutional-positioning"
      className="rounded-lg p-6 space-y-4"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      {loading && <LoadingSkeleton />}

      {error && (
        <div className="text-center py-6">
          <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>{error}</p>
        </div>
      )}

      {isEmpty && (
        <div className="text-center py-6">
          <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
            No institutional holdings data available for {ticker}
          </p>
        </div>
      )}

      {!loading && !error && !isEmpty && holdings && (
        <>
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
              INSTITUTIONAL POSITIONING
            </h2>
            {periodLabel && (
              <span
                className="text-label-sm px-2 py-0.5 rounded-sm"
                style={{
                  background: "color-mix(in srgb, var(--color-primary-muted) 10%, transparent)",
                  color: "var(--color-primary-muted)",
                }}
              >
                {periodLabel}
              </span>
            )}
          </div>

          <p className="text-xs -mt-2" style={{ color: "var(--color-text-tertiary)" }}>
            13F filings have a 45-day reporting lag from the period end date.
          </p>

          {/* Summary metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                TOTAL HOLDERS
              </span>
              <span className="text-mono-data block mt-1" style={{ color: "var(--color-on-surface)" }}>
                {holdings.summary.total_holders}
              </span>
              <span className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
                tracked institutions
              </span>
            </div>

            <div>
              <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                CURATED HOLDERS
              </span>
              <span className="text-mono-data block mt-1" style={{ color: "var(--color-on-surface)" }}>
                {holdings.summary.curated_holders}
              </span>
              <span className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
                high-conviction managers
              </span>
            </div>

            <div>
              <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                NET ACCUMULATION
              </span>
              <div className="flex items-center gap-2 mt-1">
                {netChange >= 0 ? (
                  <span
                    data-testid="net-accumulation-up"
                    className="text-2xl"
                    style={{ color: "var(--color-bullish)" }}
                    aria-label="Accumulating"
                  >
                    &#9650;
                  </span>
                ) : (
                  <span
                    data-testid="net-accumulation-down"
                    className="text-2xl"
                    style={{ color: "var(--color-bearish)" }}
                    aria-label="Distributing"
                  >
                    &#9660;
                  </span>
                )}
                <span
                  className="text-lg"
                  style={{
                    fontFamily: "var(--font-data)",
                    color: netChange >= 0 ? "var(--color-bullish)" : "var(--color-bearish)",
                  }}
                >
                  {formatSharesChange(netChange)}
                </span>
              </div>
              <span className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
                net share change
              </span>
            </div>
          </div>

          {/* Gated detailed content: trend chart, holders table, other holders */}
          <ProGate>
            {/* Holder count trend chart */}
            {chartData.length > 1 && (
              <div className="space-y-2">
                <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                  HOLDER TREND
                </span>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--color-surface-container-high)"
                        strokeOpacity={0.1}
                      />
                      <XAxis
                        dataKey="period"
                        tick={{ fontSize: 10, fontFamily: "var(--font-data)", fill: "var(--color-text-tertiary)" }}
                        stroke="var(--color-text-tertiary)"
                      />
                      <YAxis
                        tick={{ fontSize: 10, fontFamily: "var(--font-data)", fill: "var(--color-text-tertiary)" }}
                        stroke="var(--color-text-tertiary)"
                        allowDecimals={false}
                      />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="curated"
                        stroke="var(--color-primary-muted)"
                        strokeWidth={1.5}
                        dot={false}
                        name="Curated"
                      />
                      <Line
                        type="monotone"
                        dataKey="total"
                        stroke="var(--color-on-surface-variant)"
                        strokeWidth={1.5}
                        dot={false}
                        name="Total"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Curated holders table */}
            {holdings.curated_holders.length > 0 && (
              <HolderTable holders={holdings.curated_holders} label="CURATED HOLDERS" />
            )}

            {/* Expandable other holders */}
            {holdings.other_holders.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowOtherHolders((prev) => !prev)}
                  className="w-full flex items-center justify-between py-2 text-left transition-opacity hover:opacity-80"
                >
                  <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                    ALL TRACKED HOLDERS ({holdings.other_holders.length})
                  </span>
                  <span className="text-sm" style={{ color: "var(--color-text-tertiary)" }}>
                    {showOtherHolders ? "\u25B2" : "\u25BC"}
                  </span>
                </button>
                {showOtherHolders && (
                  <div className="mt-2">
                    <HolderTable holders={holdings.other_holders} label="" />
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
