"use client"

import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts"
import type { PriceBar } from "@/lib/api/types"

interface PriceChartProps {
  bars: PriceBar[] | null | undefined
  buyPrice?: number | null
  sellPrice?: number | null
  className?: string
}

type TimeRange = "1M" | "3M" | "6M" | "1Y"

const RANGE_DAYS: Record<TimeRange, number> = {
  "1M": 22,
  "3M": 66,
  "6M": 132,
  "1Y": 252,
}

export function PriceChart({
  bars,
  buyPrice,
  sellPrice,
  className = "",
}: PriceChartProps) {
  const [range, setRange] = useState<TimeRange>("3M")

  if (!bars || bars.length === 0) {
    return (
      <div
        className={`h-64 flex items-center justify-center bg-bg-secondary rounded-sm ${className}`}
        data-testid="price-chart-empty"
      >
        <span className="text-sm text-text-tertiary">
          No price data available
        </span>
      </div>
    )
  }

  const sorted = [...bars].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const sliced = sorted.slice(-RANGE_DAYS[range])

  const data = sliced.map((bar) => ({
    date: bar.date.slice(5),
    close: bar.close,
    volume: bar.volume,
    open: bar.open,
    high: bar.high,
    low: bar.low,
  }))

  return (
    <div className={className} data-testid="price-chart">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-text-primary">Price History</h4>
        <div className="flex gap-1">
          {(["1M", "3M", "6M", "1Y"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={(e) => {
                e.stopPropagation()
                setRange(r)
              }}
              className={`px-2 py-0.5 text-xs rounded-sm transition-colors ${
                range === r
                  ? "bg-accent text-bg-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data}>
          <defs>
            <linearGradient id="accentGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.15} />
              <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-grid-line)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-tertiary)" }}
            interval="preserveStartEnd"
            stroke="var(--color-grid-line)"
          />
          <YAxis
            yAxisId="price"
            domain={["auto", "auto"]}
            tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-tertiary)" }}
            width={60}
            tickFormatter={(v: number) => `$${v}`}
            stroke="var(--color-grid-line)"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border-primary)",
              borderRadius: "8px",
              fontSize: "12px",
              fontFamily: "var(--font-sans)",
              boxShadow: "var(--shadow-card)",
            }}
            labelStyle={{ fontFamily: "var(--font-display)", fontSize: "14px" }}
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <Bar
            dataKey="volume"
            fill="currentColor"
            className="text-text-tertiary"
            opacity={0.15}
            yAxisId="volume"
          />
          <Area
            type="monotone"
            dataKey="close"
            fill="url(#accentGradient)"
            stroke="none"
            yAxisId="price"
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            className="text-accent"
            yAxisId="price"
          />
          {buyPrice != null && (
            <ReferenceLine
              y={buyPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-bullish"
              label={{ value: "Buy", position: "left", fontSize: 10 }}
            />
          )}
          {sellPrice != null && (
            <ReferenceLine
              y={sellPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-warning"
              label={{ value: "Sell", position: "left", fontSize: 10 }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
