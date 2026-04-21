"use client"

import { FILTER_METADATA } from "@/lib/filter-metadata"
import { FormulaTooltip } from "@/components/ui/formula-tooltip"
import type { FilterResultResponse } from "@/lib/api/types"

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

function formatPillValue(
  value: number | null,
  name: string,
  metrics?: Record<string, number | string> | null,
): string {
  if (value == null) return "N/A"
  if (name === "fcf_distress" && metrics && "positive_years" in metrics) {
    const posYears = metrics.positive_years as number
    const totalYears = metrics.total_years as number
    return `${posYears}/${totalYears}yrs`
  }
  if (name === "liquidity") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  if (name === "interest_coverage") return `${value.toFixed(1)}x`
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
    return `\u2265 ${required}/${totalYears} years \u00b7 margin \u2265 ${Math.round(floor * 100)}%${sectorLabel}`
  }
  if (name === "liquidity") return `$${(threshold / 1e6).toFixed(0)}M`
  if (name === "interest_coverage") return `${threshold.toFixed(1)}x`
  if (name === "fcf_distress") return "Positive"
  return threshold.toFixed(2)
}

function formatMetricValue(value: number | string): string {
  if (typeof value === "string") return value
  if (Number.isInteger(value)) return String(value)
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(0)}M`
  return value.toFixed(2)
}

function formatMetricLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function shortName(displayName: string | undefined, filterName: string): string {
  if (!displayName) return filterName
  return displayName.replace(/\s+(Score|Ratio)$/, "")
}

// ─── FilterPill ────────────────────────────────────────────────────────────────

interface FilterPillProps {
  filter: FilterResultResponse
  isExpanded: boolean
  onClick: () => void
}

export function FilterPill({ filter, isExpanded, onClick }: FilterPillProps) {
  const meta = FILTER_METADATA[filter.name]
  const isInconclusive = filter.verdict === "inconclusive"
  const passed = filter.passed

  const borderColor = isInconclusive
    ? "var(--color-warning)"
    : !passed
      ? "var(--color-bearish)"
      : "var(--color-bullish)"

  const bgOpacity = isExpanded ? "15%" : "8%"
  const background = `color-mix(in srgb, ${borderColor} ${bgOpacity}, transparent)`

  const icon = isInconclusive ? "?" : passed ? "\u2713" : "\u2715"
  const iconColor = isInconclusive
    ? "var(--color-warning)"
    : passed
      ? "var(--color-bullish)"
      : "var(--color-bearish)"

  const label = shortName(meta?.displayName, filter.name)
  const valueStr = formatPillValue(filter.value, filter.name, filter.computed_metrics)

  return (
    <button
      type="button"
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs"
      style={{
        background,
        border: `1px solid ${borderColor}`,
        cursor: "pointer",
      }}
      onClick={onClick}
      data-testid={`filter-pill-${filter.name}`}
    >
      <span style={{ color: iconColor, fontWeight: 600 }}>{icon}</span>
      <span style={{ color: "var(--color-on-surface)" }}>{label}</span>
      <span style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
        {valueStr}
      </span>
    </button>
  )
}

// ─── FilterDetail ──────────────────────────────────────────────────────────────

interface FilterDetailProps {
  filter: FilterResultResponse
}

export function FilterDetail({ filter }: FilterDetailProps) {
  const meta = FILTER_METADATA[filter.name]
  const passed = filter.passed
  const isInconclusive = filter.verdict === "inconclusive"

  const metrics = filter.computed_metrics
  const hasMetrics = metrics != null && Object.keys(metrics).length > 0

  return (
    <div
      className="rounded-lg px-4 py-3 space-y-3 mt-2"
      style={{
        background: "var(--color-surface-container)",
        border: "1px solid var(--color-ghost-border)",
      }}
      data-testid={`filter-detail-${filter.name}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <FormulaTooltip metricKey={filter.name}>
          <span className="text-sm font-semibold" style={{ color: "var(--color-on-surface)" }}>
            {meta?.displayName ?? filter.name}
          </span>
        </FormulaTooltip>
        {meta?.technicalName && (
          <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
            ({meta.technicalName})
          </span>
        )}
      </div>

      {/* Computed metrics table */}
      {hasMetrics ? (
        <div>
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="text-left py-1 pr-2 text-label-sm font-medium" style={{ color: "var(--color-text-tertiary)" }}>Metric</th>
                <th className="text-right py-1 px-2 text-label-sm font-medium" style={{ color: "var(--color-text-tertiary)" }}>Value</th>
                <th className="text-right py-1 px-2 text-label-sm font-medium" style={{ color: "var(--color-text-tertiary)" }}>Threshold</th>
                <th className="text-right py-1 pl-2 text-label-sm font-medium" style={{ color: "var(--color-text-tertiary)" }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {/* Primary value vs threshold row */}
              <tr style={{ background: "var(--color-surface)" }}>
                <td className="py-1.5 pr-2" style={{ color: "var(--color-on-surface-variant)" }}>{meta?.displayName ?? filter.name}</td>
                <td className="py-1.5 px-2 text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                  {formatValue(filter.value, filter.name, metrics)}
                </td>
                <td className="py-1.5 px-2 text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                  {formatThreshold(filter.threshold, filter.name, metrics)}
                </td>
                <td
                  className="py-1.5 pl-2 text-right"
                  style={{
                    fontFamily: "var(--font-data)",
                    color: isInconclusive ? "var(--color-warning)" : passed ? "var(--color-bullish)" : "var(--color-bearish)",
                  }}
                >
                  {isInconclusive ? "INCONCLUSIVE" : passed ? "PASS" : "FAIL"}
                </td>
              </tr>
              {/* Additional computed metrics rows */}
              {Object.entries(metrics!).map(([key, val], idx) => (
                <tr key={key} style={{ background: idx % 2 === 0 ? "var(--color-surface-container-lowest)" : "var(--color-surface)" }}>
                  <td className="py-1 pr-2" style={{ color: "var(--color-text-tertiary)" }}>{formatMetricLabel(key)}</td>
                  <td className="py-1 px-2 text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }} colSpan={3}>
                    {formatMetricValue(val)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Fallback: simple value vs threshold display */
        <div className="flex items-center gap-6 text-sm">
          <div>
            <span className="text-xs block" style={{ color: "var(--color-text-tertiary)" }}>Value</span>
            <span style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
              {formatValue(filter.value, filter.name, filter.computed_metrics)}
            </span>
          </div>
          <div>
            <span className="text-xs block" style={{ color: "var(--color-text-tertiary)" }}>Threshold</span>
            <span style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
              {formatThreshold(filter.threshold, filter.name, filter.computed_metrics)}
            </span>
          </div>
          <div>
            <span className="text-xs block" style={{ color: "var(--color-text-tertiary)" }}>Result</span>
            <span
              style={{
                fontFamily: "var(--font-data)",
                color: isInconclusive ? "var(--color-warning)" : passed ? "var(--color-bullish)" : "var(--color-bearish)",
              }}
            >
              {isInconclusive ? "INCONCLUSIVE" : passed ? "PASS" : "FAIL"}
            </span>
          </div>
        </div>
      )}

      {/* Detail from API */}
      {filter.detail && (
        <p className="text-xs" style={{ color: "var(--color-on-surface-variant)" }}>{filter.detail}</p>
      )}

      {/* Formula */}
      {meta?.formula && (
        <div className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
          Formula: {meta.formula}
        </div>
      )}

      {/* Academic citation */}
      {meta?.citation && (
        <p className="text-xs italic" style={{ color: "var(--color-text-tertiary)" }}>
          Source: {meta.citation}
        </p>
      )}

      {/* WHY THIS MATTERS — only for failed filters */}
      {!passed && meta?.whyItMatters && (
        <div className="pt-2 mt-2" style={{ borderTop: "1px solid var(--color-ghost-border)" }}>
          <span
            className="text-label-sm font-semibold block mb-1"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            Why This Matters
          </span>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-on-surface-variant)" }}>
            {meta.whyItMatters}
          </p>
        </div>
      )}
    </div>
  )
}
