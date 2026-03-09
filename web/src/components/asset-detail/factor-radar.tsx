"use client"

import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
} from "recharts"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface FactorRadarProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  sectorName?: string
  variant?: "default" | "dimmed"
  onAxisClick?: (factor: string) => void
}

interface RadarDataPoint {
  axis: string
  factor: string
  stock: number
  sectorMedian: number
  sectorP90: number
}

function buildRadarData(
  quality: FactorBreakdownResponse,
  value: FactorBreakdownResponse,
  momentum: FactorBreakdownResponse
): RadarDataPoint[] {
  return [
    {
      axis: `Quality (${Math.round(quality.average_percentile)}th)`,
      factor: "Quality",
      stock: quality.average_percentile,
      sectorMedian: 50,
      sectorP90: 90,
    },
    {
      axis: `Value (${Math.round(value.average_percentile)}th)`,
      factor: "Value",
      stock: value.average_percentile,
      sectorMedian: 50,
      sectorP90: 90,
    },
    {
      axis: `Momentum (${Math.round(momentum.average_percentile)}th)`,
      factor: "Momentum",
      stock: momentum.average_percentile,
      sectorMedian: 50,
      sectorP90: 90,
    },
  ]
}

function MobileBar({
  label,
  percentile,
  onClick,
}: {
  label: string
  percentile: number
  onClick?: () => void
}) {
  return (
    <button
      className="w-full text-left space-y-1"
      onClick={onClick}
      type="button"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-text-secondary">{label}</span>
        <span className="text-xs font-mono text-text-primary">
          {Math.round(percentile)}th
        </span>
      </div>
      <div className="relative h-2 w-full rounded-full bg-white/[0.06]">
        {/* Sector median marker at 50% */}
        <div
          className="absolute top-0 h-full w-px bg-white/30"
          style={{ left: "50%" }}
        />
        {/* Sector P90 marker at 90% */}
        <div
          className="absolute top-0 h-full w-px bg-white/20"
          style={{ left: "90%" }}
        />
        {/* Stock percentile fill */}
        <div
          className="absolute top-0 left-0 h-full rounded-full"
          style={{
            width: `${Math.min(percentile, 100)}%`,
            backgroundColor: "var(--color-accent, #1A7A5A)",
            opacity: 0.7,
          }}
        />
      </div>
    </button>
  )
}

export function FactorRadar({
  quality,
  value,
  momentum,
  sectorName,
  variant = "default",
  onAxisClick,
}: FactorRadarProps) {
  const isDimmed = variant === "dimmed"
  const data = buildRadarData(quality, value, momentum)

  const fillOpacity = isDimmed ? 0.08 : 0.15
  const strokeDasharray = isDimmed ? "4 4" : undefined

  return (
    <section
      data-testid="factor-radar"
      className={`terminal-card p-6${isDimmed ? " opacity-60" : ""}`}
    >
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text-primary">
          {isDimmed ? "Hypothetical Factor Profile" : "Factor Profile"}
        </h3>
        {sectorName && (
          <p className="text-xs text-text-tertiary mt-0.5">
            vs. {sectorName} sector benchmarks
          </p>
        )}
        {isDimmed && (
          <p className="text-xs text-warning mt-1">
            This stock did not pass filters. Profile shown for reference only.
          </p>
        )}
      </div>

      {/* Desktop: Radar chart */}
      <div data-testid="radar-desktop" className="hidden md:block">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={data}>
            <PolarGrid strokeOpacity={0.3} />
            <PolarAngleAxis
              dataKey="axis"
              tick={{
                fontSize: 11,
                fontFamily: "var(--font-geist-mono)",
                fill: "var(--color-text-secondary, #A09B93)",
              }}
            />
            <Radar
              name="Sector Top 10%"
              dataKey="sectorP90"
              stroke="var(--color-text-tertiary)"
              strokeWidth={1}
              strokeDasharray="4 4"
              fill="none"
              fillOpacity={0}
            />
            <Radar
              name="Sector Median"
              dataKey="sectorMedian"
              stroke="var(--color-text-secondary)"
              strokeWidth={1.5}
              fill="none"
              fillOpacity={0}
            />
            <Radar
              name="Stock"
              dataKey="stock"
              stroke="var(--color-accent, #1A7A5A)"
              strokeWidth={2}
              strokeDasharray={strokeDasharray}
              fill="var(--color-accent, #1A7A5A)"
              fillOpacity={fillOpacity}
              /* eslint-disable @typescript-eslint/no-explicit-any -- Recharts onClick callback type mismatch */
              onClick={((_: unknown, index: number) => {
                if (onAxisClick && data[index]) {
                  onAxisClick(data[index].factor)
                }
              }) as any}
              /* eslint-enable @typescript-eslint/no-explicit-any */
            />
            <Legend
              wrapperStyle={{
                fontSize: 10,
                fontFamily: "var(--font-geist-mono)",
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Mobile: Horizontal comparison bars */}
      <div data-testid="radar-mobile" className="md:hidden space-y-3">
        <MobileBar
          label="Quality"
          percentile={quality.average_percentile}
          onClick={onAxisClick ? () => onAxisClick("Quality") : undefined}
        />
        <MobileBar
          label="Value"
          percentile={value.average_percentile}
          onClick={onAxisClick ? () => onAxisClick("Value") : undefined}
        />
        <MobileBar
          label="Momentum"
          percentile={momentum.average_percentile}
          onClick={onAxisClick ? () => onAxisClick("Momentum") : undefined}
        />
      </div>

      {/* Hint text */}
      {onAxisClick && (
        <p className="text-xs text-text-tertiary mt-3 text-center">
          Click any axis for sub-factor breakdown
        </p>
      )}
    </section>
  )
}
