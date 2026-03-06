"use client"

import { useEffect, useState } from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts"
import { HYPOTHETICAL_DISCLAIMER } from "@/lib/disclaimers"

interface EquityCurvePoint {
  month: string
  portfolio: number
  benchmark: number
}

interface PortfolioTeaser {
  model_return: number
  benchmark_return: number
  max_drawdown: number
  sharpe_ratio: number
  num_months: number
  start_date: string
  end_date: string
  equity_curve: EquityCurvePoint[]
}

function formatValue(v: number): string {
  return `$${(v / 1000).toFixed(1)}k`
}

function formatPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

function computeCAGR(totalReturn: number, months: number): number {
  if (months <= 0) return 0
  const years = months / 12
  return Math.pow(1 + totalReturn, 1 / years) - 1
}

interface MetricProps {
  label: string
  value: string
  accent?: boolean
  danger?: boolean
}

function Metric({ label, value, accent, danger }: MetricProps) {
  const colorClass = danger
    ? "text-danger"
    : accent
      ? "text-accent"
      : "text-text-primary"
  return (
    <div className="text-center">
      <div className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className={`font-mono text-sm ${colorClass}`}>{value}</div>
    </div>
  )
}

export function ProofHistoricalChart() {
  const [data, setData] = useState<PortfolioTeaser | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 10_000)

    async function load() {
      try {
        const resp = await fetch("/api/v1/backtest/portfolio-teaser", {
          signal: controller.signal,
        })
        if (resp.ok) {
          setData(await resp.json())
        } else {
          console.error("Portfolio teaser fetch failed:", resp.status)
          setError("Unable to load historical performance data.")
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          console.error("Portfolio teaser fetch timed out after 10s")
          setError("Request timed out. Please try again later.")
        } else {
          console.error("Portfolio teaser network error:", err)
          setError("Unable to load historical performance data.")
        }
      } finally {
        clearTimeout(timeout)
      }
    }
    load()

    return () => {
      controller.abort()
      clearTimeout(timeout)
    }
  }, [])

  if (error) {
    return (
      <div data-testid="historical-error" className="py-4">
        <div
          className="h-[200px] rounded-lg flex flex-col items-center justify-center gap-3"
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px dashed rgba(255,255,255,0.06)'
          }}
        >
          <div className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(26,122,90,0.1)' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 12L6 7L9 10L12 5L14 7"
                stroke="var(--color-accent)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.5"
              />
            </svg>
          </div>
          <p className="text-[11px] font-mono text-text-tertiary text-center">
            Historical application in development
          </p>
          <p className="text-[10px] text-text-tertiary text-center max-w-[200px] leading-relaxed">
            Walk-forward backtesting with point-in-time data coming soon
          </p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div data-testid="historical-skeleton">
        <div className="h-[200px] bg-border-subtle/30 animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-border-subtle/30 animate-pulse rounded" />
          ))}
        </div>
        <p className="text-xs text-text-tertiary text-center mt-4 animate-pulse">
          Loading historical data…
        </p>
      </div>
    )
  }

  const cagr = computeCAGR(data.model_return, data.num_months)
  const excessReturn = data.model_return - data.benchmark_return

  // Thin the equity curve for display — show every Nth point
  const thinned =
    data.equity_curve.length > 60
      ? data.equity_curve.filter(
          (_, i) => i === 0 || i === data.equity_curve.length - 1 || i % 6 === 0
        )
      : data.equity_curve

  return (
    <div aria-label="Historical portfolio performance compared to benchmark">
      <div className="text-xs font-mono uppercase tracking-widest text-warning/80 mb-2" data-testid="hypothetical-badge">
        Simulated Performance — Not Actual Trading Results
      </div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={thinned}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              interval={Math.max(0, Math.floor(thinned.length / 6))}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              formatter={(value, name) => [
                formatValue(Number(value)),
                name,
              ]}
              contentStyle={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}
            />
            <Area
              type="monotone"
              dataKey="portfolio"
              name="Portfolio"
              stroke="var(--color-accent)"
              strokeWidth={2}
              fill="var(--color-accent)"
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="benchmark"
              name="Benchmark"
              stroke="var(--color-text-tertiary)"
              strokeWidth={1}
              fill="none"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Metric ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <Metric label="CAGR" value={formatPct(cagr)} accent={cagr > 0} />
        <Metric
          label="Max Drawdown"
          value={`-${formatPct(Math.abs(data.max_drawdown))}`}
          danger={data.max_drawdown !== 0}
        />
        <Metric label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(2)} />
        <Metric
          label="Excess Return"
          value={formatPct(excessReturn)}
          accent={excessReturn > 0}
        />
      </div>

      <div className="mt-3 border border-warning/20 rounded p-3 bg-warning/5" data-testid="hypothetical-disclaimer">
        <p className="text-[9px] text-text-tertiary leading-relaxed">
          {HYPOTHETICAL_DISCLAIMER}
        </p>
        <p className="text-[9px] text-text-tertiary mt-1 italic">
          Walk-forward methodology: no look-ahead bias.
        </p>
      </div>
    </div>
  )
}
