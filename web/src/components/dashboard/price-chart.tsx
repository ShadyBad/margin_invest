"use client"

import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
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
          <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            className="text-text-tertiary"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            className="text-text-tertiary"
            width={60}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-elevated)",
              border: "1px solid var(--border-primary)",
              borderRadius: "2px",
              fontSize: "12px",
            }}
          />
          <Bar
            dataKey="volume"
            fill="currentColor"
            className="text-text-tertiary"
            opacity={0.15}
            yAxisId="volume"
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <Line
            type="monotone"
            dataKey="close"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            className="text-accent"
          />
          {buyPrice != null && (
            <ReferenceLine
              y={buyPrice}
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-bullish"
            />
          )}
          {sellPrice != null && (
            <ReferenceLine
              y={sellPrice}
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-warning"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
