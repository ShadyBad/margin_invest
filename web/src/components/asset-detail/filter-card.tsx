"use client"

import { FILTER_METADATA } from "@/lib/filter-metadata"
import { FormulaTooltip } from "@/components/ui/formula-tooltip"
import type { FilterResultResponse } from "@/lib/api/types"

interface FilterCardProps {
  filter: FilterResultResponse
  expanded: boolean
  sectorPassRate?: number | null
  sectorName?: string | null
}

function formatValue(
  value: number | null,
  name: string,
  metrics?: Record<string, number | string> | null,
): string {
  if (value == null) return "N/A"
  if (name === "fcf_distress" && metrics && "positive_years" in metrics) {
    const posYears = metrics.positive_years as number
    const totalYears = metrics.total_years as number
    const margin = metrics.median_fcf_margin as number
    return `${posYears}/${totalYears} years positive · FCF margin ${(margin * 100).toFixed(1)}%`
  }
  if (name === "liquidity") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  if (name === "interest_coverage") return `${value.toFixed(1)}x`
  if (name === "fcf_distress") {
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  return value.toFixed(2)
}

function formatThreshold(
  threshold: number | null,
  name: string,
  metrics?: Record<string, number | string> | null,
): string {
  if (threshold == null) return "N/A"
  if (name === "fcf_distress" && metrics && "positive_years_required" in metrics) {
    const required = metrics.positive_years_required as number
    const totalYears = metrics.total_years as number
    const floor = metrics.sector_fcf_margin_floor as number
    const sector = metrics.sector_name as string
    const sectorLabel = sector ? ` (${sector})` : ""
    return `≥ ${required}/${totalYears} years · margin ≥ ${Math.round(floor * 100)}%${sectorLabel}`
  }
  if (name === "liquidity") return `$${(threshold / 1e6).toFixed(0)}M`
  if (name === "interest_coverage") return `${threshold.toFixed(1)}x`
  if (name === "fcf_distress") return "Positive"
  return threshold.toFixed(2)
}

export function FilterCard({ filter, expanded, sectorPassRate, sectorName }: FilterCardProps) {
  const meta = FILTER_METADATA[filter.name]
  const passed = filter.passed
  const isInconclusive = filter.verdict === "inconclusive"

  const borderColor = isInconclusive
    ? "border-warning/30"
    : passed
      ? "border-white/[0.06]"
      : "border-bearish/30"

  const bgColor = isInconclusive
    ? "bg-warning/5"
    : !passed
      ? "bg-bearish/5"
      : ""

  const icon = isInconclusive ? "?" : passed ? "\u2713" : "\u2715"
  const iconColor = isInconclusive
    ? "text-warning"
    : passed
      ? "text-bullish"
      : "text-bearish"

  return (
    <div
      className={`border rounded-lg ${borderColor} ${bgColor} px-4 py-3 space-y-2`}
      data-testid={`filter-card-${filter.name}`}
    >
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className={`text-base font-semibold ${iconColor}`}>{icon}</span>
        <FormulaTooltip metricKey={filter.name}>
          <span className="text-sm font-semibold text-text-primary">
            {meta?.displayName ?? filter.name}
          </span>
        </FormulaTooltip>
        {meta?.technicalName && (
          <span className="text-xs text-text-tertiary">({meta.technicalName})</span>
        )}
        {!passed && !isInconclusive && (
          <span className="ml-auto text-xs font-mono text-bearish bg-bearish/10 px-2 py-0.5 rounded">
            FAILED
          </span>
        )}
      </div>

      {/* Value vs threshold */}
      <div className="flex items-center gap-6 text-sm font-mono">
        <div>
          <span className="text-text-tertiary text-xs block">Value</span>
          <span className="text-text-primary">{formatValue(filter.value, filter.name, filter.computed_metrics)}</span>
        </div>
        <div>
          <span className="text-text-tertiary text-xs block">Threshold</span>
          <span className="text-text-primary">{formatThreshold(filter.threshold, filter.name, filter.computed_metrics)}</span>
        </div>
      </div>

      {/* Sector context — only for failed filters when data available */}
      {!passed && sectorPassRate != null && sectorName && (
        <p className="text-xs text-tertiary mt-1.5">
          {Math.round(sectorPassRate * 100)}% of {sectorName} stocks pass this filter.
        </p>
      )}

      {/* Formula (if available) */}
      {meta?.formula && expanded && (
        <div className="text-xs text-text-tertiary font-mono">
          Formula: {meta.formula}
        </div>
      )}

      {/* Academic citation */}
      {meta?.citation && expanded && (
        <p className="text-xs text-text-tertiary italic">
          Source: {meta.citation}
        </p>
      )}

      {/* Detail from API */}
      {filter.detail && (
        <p className="text-xs text-text-secondary">{filter.detail}</p>
      )}

      {/* WHY THIS MATTERS — only for failed or inconclusive, when expanded */}
      {expanded && !passed && meta?.whyItMatters && (
        <div className="border-t border-white/[0.06] pt-2 mt-2">
          <span className="text-xs uppercase tracking-wider text-text-tertiary font-semibold block mb-1">
            Why This Matters
          </span>
          <p className="text-xs text-text-secondary leading-relaxed">{meta.whyItMatters}</p>
        </div>
      )}
    </div>
  )
}
