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

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch("/api/v1/backtest/portfolio-teaser")
        if (resp.ok) setData(await resp.json())
      } catch {
        // stay null
      }
    }
    load()
  }, [])

  if (!data) {
    return (
      <div data-testid="historical-skeleton">
        <div className="h-[200px] bg-bg-subtle animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 bg-bg-subtle animate-pulse rounded" />
          ))}
        </div>
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
    <div>
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
              formatter={(value: number, name: string) => [
                formatValue(value),
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
          value={formatPct(data.max_drawdown)}
          danger={data.max_drawdown < 0}
        />
        <Metric label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(2)} />
        <Metric
          label="Excess Return"
          value={formatPct(excessReturn)}
          accent={excessReturn > 0}
        />
      </div>

      <p className="text-[9px] text-text-tertiary mt-3 text-center italic">
        Past performance is not indicative of future results. Walk-forward methodology: no
        look-ahead bias.
      </p>
    </div>
  )
}
