"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts"
import type { SeedDetail } from "@/lib/api/model-validation"

interface SeedBoxPlotProps {
  seedDetails: SeedDetail[]
  threshold: number
}

export function SeedBoxPlot({ seedDetails, threshold }: SeedBoxPlotProps) {
  const data = seedDetails
    .slice()
    .sort((a, b) => a.seed - b.seed)
    .map((d) => ({
      name: `Seed ${d.seed}`,
      rank_ic: d.rank_ic,
      selected: d.selected,
    }))

  return (
    <div data-testid="seed-box-plot" className="terminal-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        Rank IC by Seed
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid
            horizontal
            vertical={false}
            stroke="rgba(255,255,255,0.04)"
          />
          <XAxis
            dataKey="name"
            label={{ value: "Seed", position: "insideBottom", offset: -2, fontSize: 11, fill: "#5C5955" }}
            tick={{ fontSize: 10, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            label={{ value: "Rank IC", angle: -90, position: "insideLeft", fontSize: 11, fill: "#5C5955" }}
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
            domain={[0, "auto"]}
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(4), "Rank IC"]}
            contentStyle={{
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border-primary)",
              borderRadius: "4px",
              fontSize: "12px",
            }}
          />
          <ReferenceLine
            y={threshold}
            stroke="var(--color-warning)"
            strokeDasharray="6 3"
            label={{
              value: `Threshold (${threshold})`,
              position: "right",
              fontSize: 11,
              fill: "var(--color-warning)",
            }}
          />
          <Bar dataKey="rank_ic" animationDuration={800} animationEasing="ease-out">
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.selected ? "var(--color-accent)" : "var(--color-text-tertiary)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
