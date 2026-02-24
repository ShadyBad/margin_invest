interface KnobsPanelProps {
  rebalanceFrequency: string
  topPercentile: number
  transactionCostBps: number
  slippageBps: number
  benchmarkTicker: string
  onRebalanceChange?: (value: string) => void
  onTopPercentileChange?: (value: number) => void
  onTransactionCostChange?: (value: number) => void
  onSlippageChange?: (value: number) => void
  disabled?: boolean
}

export function KnobsPanel({
  rebalanceFrequency,
  topPercentile,
  transactionCostBps,
  slippageBps,
  benchmarkTicker,
  onRebalanceChange,
  onTopPercentileChange,
  onTransactionCostChange,
  onSlippageChange,
  disabled = false,
}: KnobsPanelProps) {
  const inputClasses =
    "bg-bg-primary border border-border-primary rounded-sm px-2 py-1 text-sm text-text-primary"

  return (
    <div className="terminal-card p-4" data-testid="knobs-panel">
      <h3 className="text-xs font-semibold tracking-widest text-text-secondary mb-4">
        PARAMETERS
      </h3>

      <div className="space-y-4">
        {/* Rebalance Frequency */}
        <div className="flex items-center justify-between gap-4">
          <label className="text-sm text-text-secondary whitespace-nowrap">
            Rebalance Frequency
          </label>
          <select
            data-testid="knob-rebalance-frequency"
            className={inputClasses}
            value={rebalanceFrequency}
            onChange={(e) => onRebalanceChange?.(e.target.value)}
            disabled={disabled}
          >
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
          </select>
        </div>

        {/* Top Percentile */}
        <div className="flex items-center justify-between gap-4">
          <label className="text-sm text-text-secondary whitespace-nowrap">
            Top Percentile
          </label>
          <div className="flex items-center gap-2">
            <input
              data-testid="knob-top-percentile"
              type="range"
              min={5}
              max={50}
              step={5}
              value={topPercentile}
              onChange={(e) => onTopPercentileChange?.(Number(e.target.value))}
              disabled={disabled}
              className="w-24"
            />
            <span className="font-[family-name:var(--font-mono)] text-sm text-text-primary w-8 text-right">
              {topPercentile}%
            </span>
          </div>
        </div>

        {/* Transaction Cost */}
        <div className="flex items-center justify-between gap-4">
          <label className="text-sm text-text-secondary whitespace-nowrap">
            Transaction Cost
          </label>
          <div className="flex items-center gap-1">
            <input
              data-testid="knob-transaction-cost"
              type="number"
              className={`${inputClasses} w-20 font-[family-name:var(--font-mono)]`}
              value={transactionCostBps}
              onChange={(e) => onTransactionCostChange?.(Number(e.target.value))}
              disabled={disabled}
            />
            <span className="text-xs text-text-tertiary">bps</span>
          </div>
        </div>

        {/* Slippage */}
        <div className="flex items-center justify-between gap-4">
          <label className="text-sm text-text-secondary whitespace-nowrap">Slippage</label>
          <div className="flex items-center gap-1">
            <input
              data-testid="knob-slippage"
              type="number"
              className={`${inputClasses} w-20 font-[family-name:var(--font-mono)]`}
              value={slippageBps}
              onChange={(e) => onSlippageChange?.(Number(e.target.value))}
              disabled={disabled}
            />
            <span className="text-xs text-text-tertiary">bps</span>
          </div>
        </div>

        {/* Benchmark Ticker (read-only) */}
        <div className="flex items-center justify-between gap-4">
          <label className="text-sm text-text-secondary whitespace-nowrap">Benchmark</label>
          <span className="font-[family-name:var(--font-mono)] text-sm text-text-primary">
            {benchmarkTicker}
          </span>
        </div>
      </div>
    </div>
  )
}
