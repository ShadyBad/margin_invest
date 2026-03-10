/**
 * PriceContext — 3-row data table showing current price, target price, and margin of safety.
 *
 * Monospace numbers, clean label-value layout inside a terminal-card.
 * Margin of safety is color-coded: green (positive/upside), red (negative/downside).
 */

interface PriceContextProps {
  actualPrice: number
  buyPrice: number
  marginOfSafety: number
}

function formatPrice(price: number): string {
  return `$${price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : ""
  return `${sign}${(value * 100).toFixed(1)}%`
}

export function PriceContext({ actualPrice, buyPrice, marginOfSafety }: PriceContextProps) {
  const marginColor = marginOfSafety >= 0 ? "text-bullish" : "text-bearish"

  return (
    <div data-testid="price-context" className="terminal-card p-6">
      <h3 className="text-xs font-mono text-text-tertiary uppercase tracking-wider mb-4">
        Price Context
      </h3>
      <div className="space-y-3">
        {/* Current Price */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Current Price</span>
          <span className="font-mono text-sm font-medium text-text-primary tabular-nums">
            {formatPrice(actualPrice)}
          </span>
        </div>

        <div className="border-t border-white/[0.06]" />

        {/* Target Price */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Target Price</span>
          <span className="font-mono text-sm font-medium text-text-primary tabular-nums">
            {formatPrice(buyPrice)}
          </span>
        </div>

        <div className="border-t border-white/[0.06]" />

        {/* Margin of Safety */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Margin of Safety</span>
          <span
            className={`font-mono text-sm font-semibold tabular-nums ${marginColor}`}
            data-testid="margin-of-safety-value"
          >
            {formatPercent(marginOfSafety)}
          </span>
        </div>
      </div>
    </div>
  )
}
