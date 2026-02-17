"use client"

import { useId } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import { ChartTooltip } from "./chart-tooltip"
import { ScoreContext } from "./score-context"
import type { TimeRange } from "./time-range-selector"

export interface ScoreDataPoint {
  date: string
  score: number
  signal?: string
}

interface ScoreChartProps {
  data: ScoreDataPoint[]
  timeRange: TimeRange
  showBenchmark: boolean
  benchmarkData?: ScoreDataPoint[]
  universeRank?: string
  scoringFrequency?: string
  lastScored?: string
}

const RANGE_DAYS: Record<TimeRange, number | null> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  "ALL": null,
}

export function ScoreChart({
  data,
  timeRange,
  showBenchmark,
  benchmarkData,
  universeRank,
  scoringFrequency,
  lastScored,
}: ScoreChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="h-[320px] flex items-center justify-center"
        data-testid="score-chart-empty"
      >
        <span className="text-[13px] text-[#5C5955]">Insufficient scoring history</span>
      </div>
    )
  }

  const gradientId = useId()

  const sorted = [...data].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const rangeDays = RANGE_DAYS[timeRange]
  const sliced = rangeDays
    ? (() => {
        const cutoff = new Date()
        cutoff.setDate(cutoff.getDate() - rangeDays)
        const cutoffMs = cutoff.getTime()
        return sorted.filter((d) => new Date(d.date).getTime() >= cutoffMs)
      })()
    : sorted

  const chartData = sliced.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
  }))

  return (
    <div data-testid="score-chart" className="p-6 pb-0">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1A7A5A" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#1A7A5A" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            horizontal
            vertical={false}
            stroke="rgba(255,255,255,0.04)"
          />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis domain={[0, 100]} hide />
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ stroke: "rgba(255,255,255,0.15)", strokeDasharray: "4 2", strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="score"
            fill={`url(#${gradientId})`}
            stroke="none"
            animationDuration={800}
            animationEasing="ease-out"
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#1A7A5A"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#fff", stroke: "#1A7A5A", strokeWidth: 2 }}
            animationDuration={800}
            animationEasing="ease-out"
          />
          {showBenchmark && benchmarkData && (
            <Line
              type="monotone"
              data={benchmarkData}
              dataKey="score"
              stroke="rgba(255,255,255,0.2)"
              strokeWidth={1}
              strokeDasharray="4 2"
              dot={false}
              animationDuration={500}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <ScoreContext
        universeRank={universeRank}
        scoringFrequency={scoringFrequency}
        lastScored={lastScored}
      />
    </div>
  )
}
