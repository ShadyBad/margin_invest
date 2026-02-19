import { PriceLadder } from "./price-ladder"

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

interface PanelValuationProps {
  intrinsicValue: number | null  // This is now "Margin Invest Value"
  currentPrice: number | null
  marginOfSafety: number | null
  methods: Record<string, number> | null
  buyBelow?: number | null  // buy_price
  sellPrice?: number | null
}

export function PanelValuation({
  intrinsicValue,
  currentPrice,
  marginOfSafety,
  methods,
  buyBelow,
  sellPrice,
}: PanelValuationProps) {
  const entries = methods ? Object.entries(methods) : []

  if (entries.length === 0 && intrinsicValue == null) {
    return (
      <div data-testid="panel-valuation">
        <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>
        <p className="text-[13px] text-[#5C5955]">No valuation data</p>
      </div>
    )
  }

  const maxValue = entries.length > 0 ? Math.max(...entries.map(([, v]) => v)) : 0

  return (
    <div data-testid="panel-valuation">
      <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>

      {/* Header trio: MIV, Current Price, MoS */}
      {intrinsicValue != null && (
        <div className="mb-2">
          <div className="grid grid-cols-3 gap-2">
            <div>
              <span className="text-[10px] text-[#9A9590] uppercase tracking-wider block">Margin Invest Value</span>
              <span className="text-[16px] font-mono text-[#E8E6E3] font-medium">${intrinsicValue.toFixed(2)}</span>
            </div>
            {currentPrice != null && (
              <div>
                <span className="text-[10px] text-[#9A9590] uppercase tracking-wider block">Current Price</span>
                <span className="text-[16px] font-mono text-[#E8E6E3]">${currentPrice.toFixed(2)}</span>
              </div>
            )}
            {marginOfSafety != null && (
              <div>
                <span className="text-[10px] text-[#9A9590] uppercase tracking-wider block">Margin of Safety</span>
                <span className={`text-[16px] font-mono font-medium ${
                  marginOfSafety > 0 ? "text-[#1A7A5A]" : "text-[#C74B50]"
                }`}>
                  {Math.round(marginOfSafety * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Price Ladder */}
          <PriceLadder
            buyPrice={buyBelow ?? null}
            currentPrice={currentPrice}
            fairValue={intrinsicValue}
            sellPrice={sellPrice ?? null}
          />
        </div>
      )}

      {/* Method breakdown bars */}
      {entries.length > 0 && (
        <div className="space-y-2.5 pt-3 border-t border-white/[0.06]">
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
      )}
    </div>
  )
}
