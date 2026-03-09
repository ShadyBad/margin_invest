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
  delta?: number | null
  conviction?: string | null
}

interface ScoreChartProps {
  data: ScoreDataPoint[]
  status?: "loading" | "loaded" | "error"
  onRetry?: () => void
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
  status = "loaded",
  onRetry,
  timeRange,
  showBenchmark,
  benchmarkData,
  universeRank,
  scoringFrequency,
  lastScored,
}: ScoreChartProps) {
  const gradientId = useId()

  if (status === "loading") {
    return (
      <div
        className="h-[320px] flex items-center justify-center"
        data-testid="score-chart-loading"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-[80%] max-w-[400px] space-y-3">
            <div className="h-3 bg-surface-overlay rounded animate-pulse" />
            <div className="h-3 bg-surface-overlay rounded animate-pulse w-[90%]" />
            <div className="h-3 bg-surface-overlay rounded animate-pulse w-[70%]" />
            <div className="h-3 bg-surface-overlay rounded animate-pulse w-[85%]" />
          </div>
          <span className="text-xs text-text-tertiary/60 mt-2">Loading score history…</span>
        </div>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div
        className="h-[320px] flex flex-col items-center justify-center gap-3"
        data-testid="score-chart-error"
      >
        <span className="text-[13px] text-bearish">Unable to load score history</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-[12px] text-text-tertiary hover:text-text-primary border border-border-subtle rounded px-3 py-1 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    )
  }

  if (!data || data.length < 2) {
    return (
      <div
        className="h-[320px] flex flex-col items-center justify-center gap-2"
        data-testid="score-chart-empty"
      >
        <span className="text-[13px] text-text-tertiary">Score tracking begins after the next scoring run</span>
        <span className="text-xs text-text-tertiary/60">Scores are computed weekly</span>
      </div>
    )
  }

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
              <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            horizontal
            vertical={false}
            stroke="var(--color-grid-line)"
          />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "var(--color-text-tertiary)" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis domain={[0, 100]} hide />
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ stroke: "var(--color-divider)", strokeDasharray: "4 2", strokeWidth: 1 }}
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
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "var(--color-bg-elevated)", stroke: "var(--color-accent)", strokeWidth: 2 }}
            animationDuration={800}
            animationEasing="ease-out"
          />
          {showBenchmark && benchmarkData && (
            <Line
              type="monotone"
              data={benchmarkData}
              dataKey="score"
              stroke="var(--color-text-tertiary)"
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
