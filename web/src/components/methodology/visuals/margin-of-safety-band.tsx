"use client"

export function MarginOfSafetyBand() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-6">
        Price vs. Margin Invest Value
      </p>

      <div className="relative h-24 mb-4">
        {/* Background band zones */}
        <div className="absolute inset-y-0 left-0 right-0 flex">
          <div className="flex-[25] bg-bullish/8 rounded-l-md" />
          <div className="flex-[20] bg-accent/5" />
          <div className="flex-[30] bg-warning/5" />
          <div className="flex-[25] bg-bearish/8 rounded-r-md" />
        </div>

        {/* Zone labels */}
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-xs font-medium text-bullish">Discount</span>
          </div>
          <div className="flex-[20] flex items-center justify-center">
            <span className="text-xs font-medium text-accent">Buy Below</span>
          </div>
          <div className="flex-[30] flex items-center justify-center">
            <span className="text-xs font-medium text-text-tertiary">Fair Value</span>
          </div>
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-xs font-medium text-bearish">Overvalued</span>
          </div>
        </div>

        {/* Price markers */}
        <div className="absolute bottom-0 left-0 right-0 flex text-xs font-mono text-text-tertiary">
          <div className="flex-[25] text-center">$120</div>
          <div className="flex-[20] text-center">$145</div>
          <div className="flex-[30] text-center">$175</div>
          <div className="flex-[25] text-center">$210</div>
        </div>

        {/* Marker lines */}
        <div className="absolute inset-y-2 left-[25%] w-px bg-border-primary" />
        <div className="absolute inset-y-2 left-[45%] w-px bg-accent/30" />
        <div className="absolute inset-y-2 left-[75%] w-px bg-border-primary" />

        {/* Current price indicator */}
        <div className="absolute top-1 left-[32%] flex flex-col items-center">
          <span className="text-xs font-mono text-accent mb-0.5">$138</span>
          <div className="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[6px] border-t-accent" />
        </div>
      </div>

      <div className="flex justify-between text-xs text-text-tertiary mt-2">
        <span>Buy Below</span>
        <span>Current Price</span>
        <span>Margin Invest Value</span>
        <span>Sell Target</span>
      </div>
    </div>
  )
}
