"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts"
import { classifyTilt } from "./classify-tilt"
import type { CandidateCard } from "./types"

interface ProofTiltChartProps {
  candidates: CandidateCard[]
}

const BAR_COLORS = [
  "color-mix(in srgb, var(--color-accent), transparent 60%)", // Value — 40% opacity
  "color-mix(in srgb, var(--color-accent), transparent 40%)", // Blend — 60% opacity
  "var(--color-accent)",                                       // Growth — 100% opacity
]

const CATEGORIES = ["Value", "Blend", "Growth"] as const

export function ProofTiltChart({ candidates }: ProofTiltChartProps) {
  const counts = classifyTilt(candidates)
  const maxCount = Math.max(counts.Value, counts.Blend, counts.Growth, 1)

  if (candidates.length === 0) {
    return (
      <div>
        <div className="h-[120px] flex items-center justify-center">
          <p className="text-xs text-text-tertiary">No candidates scored yet</p>
        </div>
        <p className="text-[10px] text-text-tertiary mt-3 text-center">
          Candidates by dominant factor · Value ← Blend → Growth
        </p>
      </div>
    )
  }

  const data = CATEGORIES.map((name) => ({ name, count: counts[name] }))

  return (
    <div>
      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="20%">
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
            />
            <YAxis hide domain={[0, Math.ceil(maxCount * 1.25)]} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={28} minPointSize={2}>
              {data.map((_, i) => (
                <Cell key={CATEGORIES[i]} fill={BAR_COLORS[i]} />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                style={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Candidates by dominant factor · Value ← Blend → Growth
      </p>
    </div>
  )
}
