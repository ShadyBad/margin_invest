export interface FailedFilterComparison {
  filterName: string
  filterDisplayName: string
  stockValue: number
  threshold: number
  championValue: number | null
  championTicker: string | null
  sectorMedian: number | null
}

interface FailedComparisonProps {
  ticker: string
  failedFilters: FailedFilterComparison[]
}

function formatValue(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (abs >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toFixed(2)
}

export function FailedComparison({ ticker, failedFilters }: FailedComparisonProps) {
  if (failedFilters.length === 0) {
    return null
  }

  // Find the first non-null champion ticker for the attribution line
  const championTicker = failedFilters.find(
    (f) => f.championTicker != null && f.championValue != null
  )?.championTicker

  return (
    <section data-testid="failed-comparison" className="terminal-card p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4">
        Where {ticker} Failed, Others Passed
      </h2>

      <div className="space-y-5">
        {failedFilters.map((filter) => (
          <div key={filter.filterName} className="space-y-2">
            {/* Filter display name */}
            <span className="text-xs font-medium text-text-secondary">
              {filter.filterDisplayName}
            </span>

            {/* Stock row (FAIL) */}
            <div className="flex items-center gap-2">
              <span className="w-12 text-xs font-mono text-text-tertiary truncate">{ticker}</span>
              <div className="flex-1 h-5 rounded bg-bearish/50" />
              <span className="text-xs font-mono text-text-primary">{formatValue(filter.stockValue)}</span>
              <span className="text-[10px] font-semibold uppercase tracking-wide text-bearish">
                FAIL
              </span>
            </div>

            {/* Champion row (PASS) — only if champion data exists */}
            {filter.championTicker != null && filter.championValue != null && (
              <div className="flex items-center gap-2">
                <span className="w-12 text-xs font-mono text-text-tertiary truncate">
                  {filter.championTicker}
                </span>
                <div className="flex-1 h-5 rounded bg-bullish/50" />
                <span className="text-xs font-mono text-text-primary">
                  {formatValue(filter.championValue)}
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-bullish">
                  PASS
                </span>
              </div>
            )}

            {/* Threshold + sector median labels */}
            <div className="flex items-center gap-3">
              <span className="text-[9px] text-text-tertiary">
                Threshold: {formatValue(filter.threshold)}
              </span>
              {filter.sectorMedian != null && (
                <span className="text-[9px] text-text-tertiary">
                  Sector median: {formatValue(filter.sectorMedian)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Attribution line */}
      {championTicker && (
        <p className="text-[10px] text-text-tertiary mt-4 pt-3 border-t border-white/[0.06]">
          Comparison stock: {championTicker} (highest-scoring in same sector)
        </p>
      )}
    </section>
  )
}
