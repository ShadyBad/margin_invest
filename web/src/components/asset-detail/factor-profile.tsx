"use client"

/**
 * FactorProfile -- Consolidated radar chart + factor bars.
 *
 * Replaces the separate FactorRadar + FactorPanel pair with a single
 * card that shows a Recharts RadarChart (stock vs sector benchmarks)
 * above 5 horizontal percentile bars.
 */

import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from "recharts"

export interface FactorProfileProps {
  factors: {
    quality: number
    value: number
    momentum: number
    sentiment: number | null
    growth: number | null
  }
  sectorBenchmarks?: {
    quality: { p50: number; p90: number }
    value: { p50: number; p90: number }
    momentum: { p50: number; p90: number }
  }
  eliminated?: boolean
}

const FACTOR_KEYS = ["quality", "value", "momentum", "sentiment", "growth"] as const
type FactorKey = (typeof FACTOR_KEYS)[number]

const FACTOR_LABELS: Record<FactorKey, string> = {
  quality: "Quality",
  value: "Value",
  momentum: "Momentum",
  sentiment: "Sentiment",
  growth: "Growth",
}

interface RadarDataPoint {
  label: string
  stock: number
  p50?: number
  p90?: number
}

function buildRadarData(
  factors: FactorProfileProps["factors"],
  benchmarks?: FactorProfileProps["sectorBenchmarks"],
): RadarDataPoint[] {
  return FACTOR_KEYS.map((key) => {
    const raw = factors[key]
    const value = raw != null ? Math.min(100, Math.max(0, raw)) : 0
    const bench = benchmarks && key in benchmarks
      ? (benchmarks as Record<string, { p50: number; p90: number }>)[key]
      : undefined

    return {
      label: FACTOR_LABELS[key],
      stock: value,
      ...(bench ? { p50: bench.p50, p90: bench.p90 } : {}),
    }
  })
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function FactorBar({
  label,
  value,
  isNull,
  p50,
  p90,
  isSentiment,
}: {
  label: string
  value: number
  isNull: boolean
  p50?: number
  p90?: number
  isSentiment?: boolean
}) {
  const clamped = clamp(Math.round(value), 0, 100)

  return (
    <div className="flex items-center gap-3">
      {/* Label */}
      <span
        className="text-label-sm shrink-0"
        style={{ width: 80, color: "var(--color-on-surface-variant)" }}
      >
        {label.toUpperCase()}
      </span>

      {/* Track + fill + markers */}
      <div
        className="relative flex-1 rounded-sm overflow-visible"
        style={{
          height: isNull && isSentiment ? 6 : 8,
          background: "var(--color-surface-container-lowest)",
          ...(isNull && isSentiment
            ? {
                border: "1px dashed var(--color-text-tertiary)",
                opacity: 0.3,
              }
            : {}),
        }}
      >
        {!isNull && (
          <div
            className="absolute top-0 left-0 h-full rounded-sm"
            style={{
              width: `${clamped}%`,
              background: "var(--color-primary-container)",
            }}
          />
        )}

        {/* P50 marker */}
        {p50 != null && (
          <div
            className="absolute top-0 h-full"
            style={{
              left: `${clamp(p50, 0, 100)}%`,
              width: 1,
              background: "var(--color-on-surface-variant)",
              opacity: 0.5,
            }}
            title={`Sector P50: ${p50}`}
          />
        )}

        {/* P90 marker */}
        {p90 != null && (
          <div
            className="absolute top-0 h-full"
            style={{
              left: `${clamp(p90, 0, 100)}%`,
              width: 1,
              background: "var(--color-on-surface-variant)",
              opacity: 0.3,
            }}
            title={`Sector P90: ${p90}`}
          />
        )}
      </div>

      {/* Value */}
      <span
        className="text-label-md tabular-nums shrink-0 text-right"
        style={{
          width: isNull && isSentiment ? 64 : 32,
          fontFamily: "var(--font-data)",
          color: isNull ? "var(--color-text-tertiary)" : "var(--color-on-surface)",
          fontSize: isNull && isSentiment ? 10 : undefined,
          letterSpacing: isNull && isSentiment ? "0.05em" : undefined,
        }}
        title={isNull && isSentiment ? "Sentiment analysis available when NLP pipeline is enabled" : undefined}
      >
        {isNull && isSentiment ? "PENDING" : isNull ? "\u2014" : clamped}
      </span>
    </div>
  )
}

export function FactorProfile({
  factors,
  sectorBenchmarks,
  eliminated = false,
}: FactorProfileProps) {
  const radarData = buildRadarData(factors, sectorBenchmarks)
  const hasBenchmarks = sectorBenchmarks != null

  return (
    <section
      data-testid="factor-profile"
      className="rounded-lg p-6"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
        opacity: eliminated ? 0.6 : 1,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
          FACTOR PROFILE
        </span>
        {eliminated && (
          <span className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
            HYPOTHETICAL
          </span>
        )}
      </div>

      {/* Radar chart */}
      <div data-testid="factor-profile-radar">
        <ResponsiveContainer width="100%" height={220}>
          <RadarChart data={radarData} outerRadius="75%">
            <PolarGrid
              stroke="var(--color-surface-variant)"
              strokeOpacity={0.1}
            />
            <PolarAngleAxis
              dataKey="label"
              tick={{
                fontSize: 11,
                fontFamily: "var(--font-data)",
                fill: "var(--color-on-surface-variant)",
              }}
            />

            {/* P90 reference — dotted, faint */}
            {hasBenchmarks && (
              <Radar
                name="Sector P90"
                dataKey="p90"
                stroke="var(--color-surface-variant)"
                strokeWidth={1}
                strokeDasharray="2 3"
                strokeOpacity={0.4}
                fill="none"
                fillOpacity={0}
              />
            )}

            {/* P50 reference — dashed */}
            {hasBenchmarks && (
              <Radar
                name="Sector P50"
                dataKey="p50"
                stroke="var(--color-surface-variant)"
                strokeWidth={1}
                strokeDasharray="6 3"
                fill="none"
                fillOpacity={0}
              />
            )}

            {/* Stock data */}
            <Radar
              name="Stock"
              dataKey="stock"
              stroke="var(--color-primary-muted)"
              strokeWidth={1.5}
              fill="var(--color-primary-container)"
              fillOpacity={0.3}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Factor bars */}
      <div className="mt-6 flex flex-col gap-3" data-testid="factor-profile-bars">
        {FACTOR_KEYS.map((key) => {
          const raw = factors[key]
          const isNull = raw == null
          const value = isNull ? 0 : raw
          const bench = sectorBenchmarks && key in sectorBenchmarks
            ? (sectorBenchmarks as Record<string, { p50: number; p90: number }>)[key]
            : undefined

          return (
            <FactorBar
              key={key}
              label={FACTOR_LABELS[key]}
              value={value}
              isNull={isNull}
              p50={bench?.p50}
              p90={bench?.p90}
              isSentiment={key === "sentiment"}
            />
          )
        })}
      </div>
    </section>
  )
}
