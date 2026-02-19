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

function PriceTargetTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload as ChartPoint
  if (!data) return null

  // Determine zone
  let zone = ""
  let zoneColor = "text-zinc-400"
  if (data.price != null && data.buyPrice != null && data.sellPrice != null) {
    if (data.price <= data.buyPrice) {
      zone = "Buy Zone"
      zoneColor = "text-emerald-400"
    } else if (data.price >= data.sellPrice) {
      zone = "Sell Zone"
      zoneColor = "text-red-400"
    } else {
      zone = "Hold Zone"
      zoneColor = "text-amber-400"
    }
  }

  return (
    <div className="bg-[rgba(17,17,19,0.95)] backdrop-blur border border-white/[0.08] rounded-lg px-3 py-2 shadow-lg">
      <p className="text-[10px] font-mono text-[#5C5955] mb-1">{formatDate(String(label))}</p>
      {data.price != null && (
        <p className="text-[14px] font-mono text-blue-400">Price: ${data.price.toFixed(2)}</p>
      )}
      {data.buyPrice != null && (
        <p className="text-[11px] font-mono text-emerald-400/70">Buy: ${data.buyPrice.toFixed(2)}</p>
      )}
      {data.fairValue != null && (
        <p className="text-[11px] font-mono text-zinc-500">MIV: ${data.fairValue.toFixed(2)}</p>
      )}
      {data.sellPrice != null && (
        <p className="text-[11px] font-mono text-red-400/70">Sell: ${data.sellPrice.toFixed(2)}</p>
      )}
      {zone && (
        <p className={`text-[10px] font-mono mt-1 ${zoneColor}`}>{zone}</p>
      )}
    </div>
  )
}

export function PriceTargetChart({ scoreHistory, priceHistory }: PriceTargetChartProps) {
  const chartData = useMemo(
    () => buildChartData(scoreHistory, priceHistory),
    [scoreHistory, priceHistory],
  )

  if (chartData.length < 2) {
    return (
      <div className="px-6 py-8 border-t border-white/[0.06]" data-testid="price-target-chart-empty">
        <div className="flex flex-col items-center justify-center gap-2 text-center">
          <span className="text-[13px] text-[#5C5955]">Buy/Sell targets will appear after 2+ scoring runs</span>
          <span className="text-[11px] text-[#5C5955]/60">Target bands track how valuations evolve over time</span>
        </div>
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
            content={<PriceTargetTooltip />}
            cursor={{ stroke: "rgba(255,255,255,0.1)", strokeDasharray: "4 2" }}
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
