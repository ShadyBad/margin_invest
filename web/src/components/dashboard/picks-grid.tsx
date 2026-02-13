import { StockCard } from "./stock-card"
import { EmptyState } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

interface PicksGridProps {
  picks: PickSummary[]
  className?: string
}

export function PicksGrid({ picks, className = "" }: PicksGridProps) {
  const sorted = [...picks].sort(
    (a, b) => b.composite_percentile - a.composite_percentile,
  )

  if (sorted.length === 0) {
    return (
      <EmptyState
        title="No picks yet"
        description="Scored stocks with exceptional or high conviction will appear here."
        className={className}
      />
    )
  }

  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}
      data-testid="picks-grid"
    >
      {sorted.map((pick) => (
        <StockCard key={pick.ticker} pick={pick} />
      ))}
    </div>
  )
}
