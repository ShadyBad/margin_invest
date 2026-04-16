/**
 * VitalSigns — 5-metric horizontal strip replacing PriceContext.
 *
 * Shows current price, target price, margin of safety, composite percentile,
 * and filter pass rate in a clean grid layout with no card wrapper.
 */

interface VitalSignsProps {
  currentPrice: number | null
  targetPrice: number | null
  marginOfSafety: number | null
  compositePercentile: number
  filtersPassed: number
  filtersTotal: number
  eliminated: boolean
  consistencyWarnings?: string[]
}

function formatPrice(price: number | null): string {
  if (price == null) return "\u2014"
  return `$${price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPercent(value: number | null): string {
  if (value == null) return "\u2014"
  const sign = value >= 0 ? "+" : ""
  return `${sign}${(value * 100).toFixed(1)}%`
}

function getMarginColor(value: number | null): string {
  if (value == null) return "var(--color-on-surface)"
  return value >= 0 ? "var(--color-bullish)" : "var(--color-bearish)"
}

function getFilterColor(passed: number, total: number): string {
  if (total === 0) return "var(--color-on-surface)"
  const ratio = passed / total
  if (ratio >= 1) return "var(--color-primary-muted)"
  if (ratio >= 0.5) return "var(--color-warning)"
  return "var(--color-bearish)"
}

function WarningDot({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null
  return (
    <span
      className="inline-block rounded-full ml-1.5 align-middle"
      style={{
        width: 6,
        height: 6,
        background: "var(--color-warning)",
      }}
      title={warnings.join("; ")}
    />
  )
}

export function VitalSigns({
  currentPrice,
  targetPrice,
  marginOfSafety,
  compositePercentile,
  filtersPassed,
  filtersTotal,
  eliminated,
  consistencyWarnings = [],
}: VitalSignsProps) {
  return (
    <div
      data-testid="vital-signs"
      className="grid grid-cols-2 md:grid-cols-5 gap-6 py-6 px-6"
      style={{ background: "var(--color-surface)" }}
    >
      {/* Current Price */}
      <div>
        <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
          {formatPrice(currentPrice)}
        </div>
        <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          CURRENT PRICE
        </div>
      </div>

      {/* Target Price */}
      <div>
        <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
          {eliminated ? "\u2014" : formatPrice(targetPrice)}
        </div>
        <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          TARGET PRICE
        </div>
      </div>

      {/* Margin of Safety */}
      <div>
        <div
          className="text-mono-data"
          style={{
            color: eliminated ? "var(--color-on-surface)" : getMarginColor(marginOfSafety),
          }}
          data-testid="margin-of-safety-value"
        >
          {eliminated ? "\u2014" : formatPercent(marginOfSafety)}
        </div>
        <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          MARGIN OF SAFETY
          {consistencyWarnings.length > 0 && <WarningDot warnings={consistencyWarnings} />}
        </div>
      </div>

      {/* Percentile */}
      <div>
        <div
          className="text-mono-data"
          style={{
            color: eliminated ? "var(--color-text-tertiary)" : "var(--color-on-surface)",
          }}
        >
          {Math.round(compositePercentile)}th
        </div>
        <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          PERCENTILE
        </div>
      </div>

      {/* Filters */}
      <div>
        <div
          className="text-mono-data"
          style={{ color: getFilterColor(filtersPassed, filtersTotal) }}
        >
          {filtersPassed}/{filtersTotal}
        </div>
        <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          FILTERS PASSED
        </div>
      </div>
    </div>
  )
}
