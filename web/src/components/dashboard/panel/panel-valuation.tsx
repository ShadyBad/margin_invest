const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

interface PanelValuationProps {
  intrinsicValue: number | null
  currentPrice: number | null
  marginOfSafety: number | null
  methods: Record<string, number> | null
  buyBelow?: number | null
}

export function PanelValuation({
  intrinsicValue,
  currentPrice,
  marginOfSafety,
  methods,
  buyBelow,
}: PanelValuationProps) {
  const entries = methods ? Object.entries(methods) : []

  if (entries.length === 0) {
    return (
      <div data-testid="panel-valuation">
        <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>
        <p className="text-[13px] text-[#5C5955]">No valuation data</p>
      </div>
    )
  }

  const maxValue = Math.max(...entries.map(([, v]) => v))

  return (
    <div data-testid="panel-valuation">
      <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>

      {intrinsicValue != null && (
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-[12px] text-[#9A9590]">Intrinsic Value:</span>
            <span className="text-[16px] font-mono text-[#E8E6E3]">${intrinsicValue.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-[12px]">
            {currentPrice != null && (
              <span className="text-[#9A9590]">Current: ${currentPrice.toFixed(2)}</span>
            )}
            {currentPrice != null && marginOfSafety != null && (
              <span className="text-[#5C5955]">&middot;</span>
            )}
            {marginOfSafety != null && (
              <span className="text-[12px]">
                <span className="text-[#9A9590]">MoS: </span>
                <span className={marginOfSafety > 0 ? "text-[#1A7A5A] font-mono font-medium" : "text-[#C74B50] font-mono"}>
                  {Math.round(marginOfSafety * 100)}%
                </span>
              </span>
            )}
          </div>
        </div>
      )}

      {buyBelow != null && (
        <div className="mb-4 pt-3 border-t border-white/[0.06]">
          <div className="flex items-baseline gap-2">
            <span className="text-[12px] text-[#9A9590]">Buy Below</span>
            <span
              className={`text-[18px] font-mono font-medium ${
                currentPrice != null && currentPrice < buyBelow
                  ? "text-[#1A7A5A]"
                  : "text-[#9A9590]"
              }`}
            >
              ${buyBelow.toFixed(2)}
            </span>
          </div>
          <p className="text-[11px] text-[#5C5955] mt-1 leading-relaxed">
            {currentPrice != null && currentPrice < buyBelow
              ? "This stock trades below our entry price. Based on its fundamentals, it looks attractively priced right now."
              : "Consider waiting for a pullback before buying. This stock trades above our fundamentals-based entry price."}
          </p>
        </div>
      )}

      <div className="space-y-2.5">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-[12px] text-[#9A9590] w-[120px] shrink-0">
              {METHOD_LABELS[key] ?? key}
            </span>
            <div className="flex-1 h-[3px] rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-[#1A7A5A]/40"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
            <span className="text-[12px] font-mono text-[#E8E6E3] w-16 text-right">${value.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
