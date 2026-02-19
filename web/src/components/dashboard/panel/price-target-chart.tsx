"use client"

import { useMemo } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import type { ScoreHistoryPoint } from "@/lib/api/types"

interface PriceTargetChartProps {
  scoreHistory: ScoreHistoryPoint[]
  priceHistory?: { date: string; close: number }[]
}

interface ChartPoint {
  date: string
  price: number | null
  buyPrice: number | null
  fairValue: number | null
  sellPrice: number | null
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function formatPrice(value: number): string {
  return `$${value.toFixed(0)}`
}

/**
 * Merge daily price bars with per-run target prices using
 * last-observation-carried-forward (LOCF).
 */
function buildChartData(
  scoreHistory: ScoreHistoryPoint[],
  priceHistory?: { date: string; close: number }[],
): ChartPoint[] {
  // If we have daily price history, use it as the time axis
  if (priceHistory && priceHistory.length > 0) {
    // Sort score history by date for LOCF
    const sorted = [...scoreHistory].sort(
      (a, b) => new Date(a.scored_at).getTime() - new Date(b.scored_at).getTime(),
    )

    return priceHistory.map((bar) => {
      const barTime = new Date(bar.date).getTime()
      // Find the most recent score run at or before this date
      let match: ScoreHistoryPoint | null = null
      for (const pt of sorted) {
        if (new Date(pt.scored_at).getTime() <= barTime) {
          match = pt
        } else {
          break
        }
      }
      return {
        date: bar.date,
        price: bar.close,
        buyPrice: match?.buy_price ?? null,
        fairValue: match?.margin_invest_value ?? null,
        sellPrice: match?.sell_price ?? null,
      }
    })
  }

  // Fallback: use score history points only
  return scoreHistory.map((pt) => ({
    date: pt.scored_at,
    price: pt.actual_price,
    buyPrice: pt.buy_price,
    fairValue: pt.margin_invest_value,
    sellPrice: pt.sell_price,
  }))
}

export function PriceTargetChart({ scoreHistory, priceHistory }: PriceTargetChartProps) {
  const chartData = useMemo(
    () => buildChartData(scoreHistory, priceHistory),
    [scoreHistory, priceHistory],
  )

  if (chartData.length === 0) {
    return (
      <div className="p-6 text-center text-zinc-500 text-sm">
        No price target data available
      </div>
    )
  }

  // Find the domain for the Y axis
  const allValues = chartData.flatMap((d) =>
    [d.price, d.buyPrice, d.fairValue, d.sellPrice].filter(
      (v): v is number => v != null,
    ),
  )
  const minVal = Math.min(...allValues)
  const maxVal = Math.max(...allValues)
  const padding = (maxVal - minVal) * 0.1 || 10
  const yDomain: [number, number] = [
    Math.floor(minVal - padding),
    Math.ceil(maxVal + padding),
  ]

  return (
    <div className="px-6 py-4 border-t border-white/[0.06]">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
          Price vs Target Band
        </h3>
        <div className="flex items-center gap-4 text-[10px] text-zinc-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-px bg-blue-400 inline-block" /> Price
          </span>
          <span className="flex items-center gap-1">
            <span
              className="w-3 h-px bg-emerald-400 inline-block"
              style={{ borderTop: "1px dashed" }}
            />{" "}
            Buy
          </span>
          <span className="flex items-center gap-1">
            <span
              className="w-3 h-px bg-zinc-500 inline-block"
              style={{ borderTop: "1px dotted" }}
            />{" "}
            Fair
          </span>
          <span className="flex items-center gap-1">
            <span
              className="w-3 h-px bg-red-400 inline-block"
              style={{ borderTop: "1px dashed" }}
            />{" "}
            Sell
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            domain={yDomain}
            tickFormatter={formatPrice}
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#18181b",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: "11px",
            }}
            labelFormatter={(label: unknown) => formatDate(String(label))}
            formatter={(value: unknown, name: unknown) => {
              const numVal = Number(value)
              const strName = String(name)
              const label =
                {
                  price: "Price",
                  buyPrice: "Buy Target",
                  fairValue: "Fair Value",
                  sellPrice: "Sell Target",
                }[strName] ?? strName
              return [`$${numVal.toFixed(2)}`, label]
            }}
          />
          {/* Buy price — dashed green */}
          <Line
            type="stepAfter"
            dataKey="buyPrice"
            stroke="#34d399"
            strokeWidth={1}
            strokeDasharray="6 3"
            dot={false}
            connectNulls
          />
          {/* Fair value — dotted gray */}
          <Line
            type="stepAfter"
            dataKey="fairValue"
            stroke="#71717a"
            strokeWidth={1}
            strokeDasharray="2 2"
            dot={false}
            connectNulls
          />
          {/* Sell price — dashed red */}
          <Line
            type="stepAfter"
            dataKey="sellPrice"
            stroke="#f87171"
            strokeWidth={1}
            strokeDasharray="6 3"
            dot={false}
            connectNulls
          />
          {/* Actual price — solid blue */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
