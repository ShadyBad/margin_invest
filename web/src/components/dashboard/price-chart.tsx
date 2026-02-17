"use client"

import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  CartesianGrid,
} from "recharts"
import { CustomCrosshair } from "./custom-crosshair"
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
        className={`h-[320px] flex items-center justify-center bg-bg-secondary rounded-sm ${className}`}
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
    <div
      className={`relative border border-border-primary/50 rounded-sm animate-chart-glow ${className}`}
      data-testid="price-chart"
    >
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h4 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary">
          Price History
        </h4>
        <div className="flex gap-1.5">
          {(["1M", "3M", "6M", "1Y"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={(e) => {
                e.stopPropagation()
                setRange(r)
              }}
              className={`px-2 py-0.5 text-xs font-mono tracking-wide rounded-sm transition-colors ${
                range === r
                  ? "bg-accent text-bg-primary shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 16 }}>
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="opacity-10" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fontFamily: "var(--font-geist-mono)" }}
            interval="preserveStartEnd"
            className="text-text-tertiary"
          />
          <YAxis
            yAxisId="price"
            domain={["auto", "auto"]}
            tick={{ fontSize: 10, fontFamily: "var(--font-geist-mono)" }}
            className="text-text-tertiary"
            width={60}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip
            content={({ active, payload, label }) => (
              <CustomCrosshair
                active={!!active}
                payload={(payload ?? []).map((p) => ({
                  dataKey: String(p.dataKey),
                  value: Number(p.value),
                  color: String(p.color ?? ""),
                }))}
                label={String(label)}
              />
            )}
            cursor={{ stroke: "var(--text-tertiary)", strokeDasharray: "4 2", strokeWidth: 1 }}
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <Bar
            dataKey="volume"
            fill="currentColor"
            className="text-text-tertiary"
            opacity={0.08}
            yAxisId="volume"
          />
          <Area
            type="monotone"
            dataKey="close"
            fill="url(#priceGradient)"
            stroke="none"
            yAxisId="price"
            animationDuration={800}
            animationEasing="ease-out"
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="currentColor"
            strokeWidth={2}
            dot={false}
            className="text-accent"
            yAxisId="price"
            animationDuration={800}
            animationEasing="ease-out"
          />
          {buyPrice != null && sellPrice != null && (
            <ReferenceArea
              y1={buyPrice}
              y2={sellPrice}
              yAxisId="price"
              fill="var(--accent)"
              fillOpacity={0.04}
            />
          )}
          {buyPrice != null && (
            <ReferenceLine
              y={buyPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-bullish"
              label={{
                value: "Buy",
                position: "right",
                fontSize: 10,
                fontFamily: "var(--font-geist-mono)",
              }}
            />
          )}
          {sellPrice != null && (
            <ReferenceLine
              y={sellPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-warning"
              label={{
                value: "Sell",
                position: "right",
                fontSize: 10,
                fontFamily: "var(--font-geist-mono)",
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
