export interface ShadowPosition {
  ticker: string
  weight: number
}

export interface ShadowSectionProps {
  startDate: string
  totalReturn: number
  maxDrawdown: number
  numDays: number
  positions: ShadowPosition[]
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatWeight(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function ShadowSection({
  startDate,
  totalReturn,
  maxDrawdown,
  numDays,
  positions,
}: ShadowSectionProps) {
  return (
    <div className="terminal-card p-6" data-testid="shadow-section">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold tracking-widest text-text-secondary uppercase">
          Shadow Portfolio
        </h3>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-accent/10 border border-accent/30 text-accent text-xs font-semibold tracking-wide">
          Cannot be backdated
        </span>
      </div>

      <p className="text-sm text-text-secondary mb-4">
        Tracking since{" "}
        <span className="font-[family-name:var(--font-mono)] text-text-primary">
          {startDate}
        </span>
      </p>

      <div className="grid grid-cols-3 gap-6 mb-6">
        <div>
          <p className="text-xs text-text-tertiary mb-1">Total Return</p>
          <p
            className={`text-lg font-semibold font-[family-name:var(--font-mono)] ${
              totalReturn >= 0 ? "text-bullish" : "text-bearish"
            }`}
          >
            {totalReturn >= 0 ? "+" : ""}
            {formatPercent(totalReturn)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-tertiary mb-1">Max Drawdown</p>
          <p className="text-lg font-semibold font-[family-name:var(--font-mono)] text-bearish">
            {formatPercent(maxDrawdown)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-tertiary mb-1">Days Tracked</p>
          <p className="text-lg font-semibold font-[family-name:var(--font-mono)] text-text-primary">
            {numDays}
          </p>
        </div>
      </div>

      <div className="border-t border-border-primary pt-4">
        <h4 className="text-xs text-text-tertiary uppercase tracking-wider mb-3">
          Current Positions
        </h4>
        {positions.length === 0 ? (
          <p className="text-sm text-text-secondary">
            Tracking has just begun. Positions will appear after the first
            rebalance.
          </p>
        ) : (
          <div className="space-y-2">
            {positions.map((pos) => (
              <div
                key={pos.ticker}
                className="flex items-center justify-between py-1"
              >
                <span className="font-[family-name:var(--font-mono)] text-sm text-text-primary font-semibold">
                  {pos.ticker}
                </span>
                <span className="font-[family-name:var(--font-mono)] text-sm text-text-secondary">
                  {formatWeight(pos.weight)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
