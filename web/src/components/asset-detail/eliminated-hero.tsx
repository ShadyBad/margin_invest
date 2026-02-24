import { formatScoredAt } from "@/lib/format"

interface EliminatedHeroProps {
  ticker: string
  name: string
  sector?: string | null
  growthStage?: string | null
  actualPrice?: number | null
  failedCount: number
  totalFilters: number
  dataCoverage: number
  scoredAt?: string | null
}

function formatGrowthStage(stage: string): string {
  return stage
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ")
}

export function EliminatedHero({
  ticker,
  name,
  sector,
  growthStage,
  actualPrice,
  failedCount,
  totalFilters,
  dataCoverage,
  scoredAt,
}: EliminatedHeroProps) {
  const coveragePct = Math.round(dataCoverage * 100)

  return (
    <section data-testid="eliminated-hero" className="space-y-4">
      {/* Ticker + Name + Sector row */}
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-display font-bold text-text-primary">{ticker}</h1>
          <span className="text-lg text-text-secondary">{name}</span>
        </div>
        {(sector || growthStage) && (
          <div className="flex items-center gap-2 text-sm text-text-tertiary">
            {sector && <span>{sector}</span>}
            {sector && growthStage && <span>·</span>}
            {growthStage && <span>{formatGrowthStage(growthStage)}</span>}
          </div>
        )}
      </div>

      {/* Price line */}
      {actualPrice != null && (
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-semibold text-text-primary">
            ${actualPrice.toFixed(2)}
          </span>
        </div>
      )}

      {/* Elimination banner */}
      <div
        data-testid="eliminated-banner"
        className="border border-bearish/30 bg-bearish/5 rounded-md p-4"
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-bearish font-semibold text-sm uppercase tracking-wide">
            Eliminated
          </span>
        </div>
        <p className="text-sm text-text-secondary">
          Failed {failedCount} of {totalFilters} elimination filters.
        </p>
      </div>

      {/* Metadata ribbon */}
      <div
        data-testid="metadata-ribbon"
        className="text-xs text-text-tertiary flex items-center gap-1 flex-wrap"
      >
        <span>Data coverage: {coveragePct}%</span>
        <span>·</span>
        <span>Scored: {scoredAt ? formatScoredAt(scoredAt) : "N/A"}</span>
      </div>
    </section>
  )
}
