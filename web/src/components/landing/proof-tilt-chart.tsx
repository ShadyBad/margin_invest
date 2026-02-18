"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
} from "recharts"

const data = [
  { name: "Growth", weight: 35 },
  { name: "Value", weight: 25 },
]

export function ProofTiltChart() {
  return (
    <div>
      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" barCategoryGap="30%">
            <XAxis type="number" domain={[0, 50]} hide />
            <YAxis
              type="category"
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
              width={60}
            />
            <Bar dataKey="weight" radius={[0, 4, 4, 0]} barSize={16}>
              <Cell fill="var(--color-accent)" />
              <Cell fill="color-mix(in srgb, var(--color-accent), transparent 60%)" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Factor weights adapt by growth stage.
      </p>
    </div>
  )
}
