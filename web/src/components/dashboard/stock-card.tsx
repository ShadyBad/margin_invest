import { PercentileBar, ConvictionBadge, SignalBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

interface StockCardProps {
  pick: PickSummary
  className?: string
}

export function StockCard({ pick, className = "" }: StockCardProps) {
  return (
    <div
      className={`bg-bg-secondary border border-border rounded-xl p-6 ${className}`}
      data-testid={`stock-card-${pick.ticker}`}
    >
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
        <ConvictionBadge level={pick.conviction_level} />
      </div>

      <p className="text-sm text-text-secondary mb-4 truncate">{pick.name}</p>

      <div className="flex items-center justify-between mb-4">
        <span className="text-3xl font-bold text-gold">
          {pick.composite_percentile.toFixed(0)}
        </span>
        <SignalBadge signal={pick.signal} />
      </div>

      <div className="space-y-2">
        <PercentileBar value={pick.quality_percentile} label="Quality" />
        <PercentileBar value={pick.value_percentile} label="Value" />
        <PercentileBar value={pick.momentum_percentile} label="Momentum" />
      </div>
    </div>
  )
}
