"use client"

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
} from "recharts"

const data = [
  { stage: "Universe", score: 50, label: "Enters pipeline" },
  { stage: "Filters", score: 55, label: "Passes all 6 checks" },
  { stage: "Scoring", score: 72, label: "Factor percentiles" },
  { stage: "Conviction", score: 82, label: "Dual-track gates" },
  { stage: "ML", score: 85, label: "ML refinement" },
  { stage: "Smart $", score: 88, label: "13F overlay" },
  { stage: "Sizing", score: 91, label: "Final output" },
]

const convictionBands = [
  { y: 70, label: "Watchlist", color: "var(--color-text-tertiary)" },
  { y: 85, label: "High", color: "var(--color-warning)" },
  { y: 95, label: "Exceptional", color: "var(--color-accent)" },
]

export function CandidateJourneyChart() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="flex items-baseline justify-between mb-6">
        <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase">
          Example candidate journey
        </p>
        <span className="text-[11px] font-mono text-text-tertiary">7-stage pipeline</span>
      </div>

      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border-subtle)"
              vertical={false}
            />
            <XAxis
              dataKey="stage"
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-border-subtle)" }}
            />
            <YAxis
              domain={[40, 100]}
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-primary)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "var(--color-text-secondary)" }}
              itemStyle={{ color: "var(--color-accent)" }}
            />
            {convictionBands.map((band) => (
              <ReferenceLine
                key={band.label}
                y={band.y}
                stroke={band.color}
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
            ))}
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={{ r: 4, fill: "var(--color-accent)" }}
              activeDot={{ r: 6, fill: "var(--color-accent)" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 mt-4">
        {convictionBands.map((band) => (
          <div key={band.label} className="flex items-center gap-1.5">
            <div
              className="w-4 h-px"
              style={{
                backgroundColor: band.color,
                borderTop: `1px dashed ${band.color}`,
              }}
            />
            <span className="text-[11px] text-text-tertiary">{band.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
