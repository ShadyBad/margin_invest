"use client"

import { useEffect, useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts"
import type { CandidateCard } from "./types"

interface ProofSectorChartProps {
  candidates: CandidateCard[]
}

interface SectorRow {
  sector: string
  exceptional: number
  high: number
  medium: number
  total: number
}

function aggregateBySector(candidates: CandidateCard[]): SectorRow[] {
  const map = new Map<string, SectorRow>()

  for (const c of candidates) {
    const sector = c.sector || "Unknown"
    if (!map.has(sector)) {
      map.set(sector, { sector, exceptional: 0, high: 0, medium: 0, total: 0 })
    }
    const row = map.get(sector)!
    if (c.composite_tier === "exceptional") row.exceptional++
    else if (c.composite_tier === "high") row.high++
    else row.medium++
    row.total++
  }

  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}

function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(false)
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 639px)")
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initializing from matchMedia only available client-side
    setNarrow(mql.matches)
    const handler = (e: MediaQueryListEvent) => setNarrow(e.matches)
    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }, [])
  return narrow
}

export function ProofSectorChart({ candidates }: ProofSectorChartProps) {
  const isNarrow = useIsNarrow()

  if (candidates.length === 0) {
    return (
      <div>
        <div className="h-[180px] flex items-center justify-center">
          <p className="text-xs text-text-tertiary">
            Scoring in progress — sector breakdown updates after each scoring run.
          </p>
        </div>
      </div>
    )
  }

  const data = aggregateBySector(candidates)
  const chartHeight = Math.max(180, data.length * 32)

  return (
    <div aria-label="Sector breakdown of candidates by composite tier">
      <div style={{ height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" barCategoryGap="20%">
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--color-text-tertiary)" }}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="sector"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--color-text-secondary)" }}
              width={120}
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "var(--color-text-tertiary)" }}
            />
            <Bar
              dataKey="exceptional"
              name="Exceptional"
              fill="var(--color-accent)"
              radius={[0, 4, 4, 0]}
              barSize={isNarrow ? 16 : 8}
              stackId={isNarrow ? "stack" : undefined}
            />
            <Bar
              dataKey="high"
              name="High"
              fill="color-mix(in srgb, var(--color-accent), transparent 40%)"
              radius={[0, 4, 4, 0]}
              barSize={isNarrow ? 16 : 8}
              stackId={isNarrow ? "stack" : undefined}
            />
            <Bar
              dataKey="medium"
              name="Medium"
              fill="color-mix(in srgb, var(--color-warning), transparent 40%)"
              radius={[0, 4, 4, 0]}
              barSize={isNarrow ? 16 : 8}
              stackId={isNarrow ? "stack" : undefined}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Candidates by sector and composite tier
      </p>
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Scoring is sector-neutral. Distribution reflects where quality + value currently
        concentrate.
      </p>
    </div>
  )
}
