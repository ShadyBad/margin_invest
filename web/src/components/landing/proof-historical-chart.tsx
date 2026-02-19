"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts"

const data = [
  { month: "Jan", portfolio: 2.1, benchmark: 1.4 },
  { month: "Feb", portfolio: 3.8, benchmark: 2.1 },
  { month: "Mar", portfolio: 1.5, benchmark: 0.8 },
  { month: "Apr", portfolio: 5.2, benchmark: 3.0 },
  { month: "May", portfolio: 6.8, benchmark: 4.2 },
  { month: "Jun", portfolio: 5.4, benchmark: 3.8 },
  { month: "Jul", portfolio: 8.1, benchmark: 5.5 },
  { month: "Aug", portfolio: 9.3, benchmark: 6.1 },
  { month: "Sep", portfolio: 7.8, benchmark: 5.8 },
  { month: "Oct", portfolio: 11.2, benchmark: 7.4 },
  { month: "Nov", portfolio: 13.1, benchmark: 8.2 },
  { month: "Dec", portfolio: 15.4, benchmark: 9.1 },
]

const pctFormatter = (value: number | undefined) => `${value ?? 0}%`

export function ProofHistoricalChart() {
  return (
    <div>
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={pctFormatter}
              tick={{ fontSize: 10, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              formatter={pctFormatter}
              contentStyle={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            />
            <ReferenceLine y={0} stroke="var(--color-border-subtle)" />
            <Line
              type="monotone"
              dataKey="portfolio"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={false}
              name="Portfolio"
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke="var(--color-text-tertiary)"
              strokeWidth={1}
              dot={false}
              name="Benchmark"
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[9px] text-text-tertiary mt-3 text-center italic">
        Past performance is not indicative of future results.
      </p>
    </div>
  )
}
