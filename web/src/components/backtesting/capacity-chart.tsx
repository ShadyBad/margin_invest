"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"

export interface CapacityRow {
  aum: number
  cagr: number
  sharpe: number
  avg_impact_bps: number
}

export interface CapacityChartProps {
  rows: CapacityRow[]
  breakevenAum: number | null
}

function formatAum(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(0)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
  return `$${value.toLocaleString()}`
}

export function CapacityChart({ rows, breakevenAum }: CapacityChartProps) {
  return (
    <div className="terminal-card p-4">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid
            horizontal
            vertical={false}
            stroke="rgba(255,255,255,0.04)"
          />
          <XAxis
            dataKey="aum"
            scale="log"
            domain={["dataMin", "dataMax"]}
            tickFormatter={formatAum}
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            dataKey="sharpe"
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
            domain={[0, "auto"]}
          />
          <Tooltip
            formatter={(value: number | undefined) => [value?.toFixed(2) ?? "—", "Sharpe"]}
            labelFormatter={(label: string | number) => formatAum(Number(label))}
            contentStyle={{
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border-primary)",
              borderRadius: "4px",
              fontSize: "12px",
            }}
          />
          <ReferenceLine
            y={0.5}
            stroke="var(--color-warning)"
            strokeDasharray="6 3"
            label={{
              value: "Sharpe = 0.5",
              position: "right",
              fontSize: 11,
              fill: "var(--color-warning)",
            }}
          />
          <Line
            type="monotone"
            dataKey="sharpe"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-accent)" }}
            activeDot={{ r: 5, fill: "#fff", stroke: "var(--color-accent)", strokeWidth: 2 }}
            animationDuration={800}
            animationEasing="ease-out"
          />
        </LineChart>
      </ResponsiveContainer>
      {breakevenAum !== null && (
        <p className="text-xs text-warning mt-2" data-testid="breakeven-callout">
          Strategy degrades below Sharpe 0.5 at {formatAum(breakevenAum)}
        </p>
      )}
    </div>
  )
}
