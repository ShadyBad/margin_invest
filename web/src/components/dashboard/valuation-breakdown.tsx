interface ValuationBreakdownProps {
  methods: Record<string, number> | null | undefined
  intrinsicValue: number | null | undefined
  className?: string
}

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

export function ValuationBreakdown({
  methods,
  intrinsicValue,
  className = "",
}: ValuationBreakdownProps) {
  if (!methods || Object.keys(methods).length === 0) {
    return (
      <div className={`${className}`} data-testid="valuation-empty">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Valuation</h4>
        <p className="text-sm text-text-tertiary">No valuation data available</p>
      </div>
    )
  }

  const entries = Object.entries(methods)
  const maxValue = Math.max(...entries.map(([, v]) => v))

  return (
    <div className={className} data-testid="valuation-breakdown">
      <h4 className="text-sm font-semibold text-text-primary mb-3">Valuation Methods</h4>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-text-secondary w-28 shrink-0">
              {METHOD_LABELS[key] ?? key}
            </span>
            <div className="flex-1 h-4 bg-bg-secondary rounded-sm overflow-hidden">
              <div
                className="h-full bg-accent/40 rounded-sm"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
            <span className="text-xs text-text-primary font-medium w-16 text-right">
              ${value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
      {intrinsicValue != null && (
        <div className="mt-3 pt-3 border-t border-border-primary flex justify-between text-sm">
          <span className="text-text-secondary">Consensus</span>
          <span className="text-text-primary font-semibold">${intrinsicValue.toFixed(2)}</span>
        </div>
      )}
    </div>
  )
}
