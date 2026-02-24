import { FilterCard } from "./filter-card"
import type { FilterResultResponse } from "@/lib/api/types"

interface EliminationGauntletProps {
  filters: FilterResultResponse[]
  eliminated: boolean
}

export function EliminationGauntlet({ filters, eliminated }: EliminationGauntletProps) {
  const passCount = filters.filter((f) => f.passed).length

  // When eliminated, sort failed filters to top
  const sortedFilters = eliminated
    ? [...filters].sort((a, b) => {
        if (a.passed === b.passed) return 0
        return a.passed ? 1 : -1
      })
    : filters

  return (
    <section data-testid="elimination-gauntlet" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Elimination Gauntlet</h2>
          <p className="text-xs text-text-tertiary mt-0.5">
            Every scored stock must survive all six filters.
          </p>
        </div>
        <span
          className={`text-sm font-mono px-2 py-1 rounded ${
            passCount === filters.length
              ? "text-bullish bg-bullish/10"
              : "text-bearish bg-bearish/10"
          }`}
        >
          {passCount} of {filters.length} passed
        </span>
      </div>

      <div className="space-y-2">
        {sortedFilters.map((filter) => (
          <FilterCard
            key={filter.name}
            filter={filter}
            expanded={eliminated ? !filter.passed : false}
          />
        ))}
      </div>
    </section>
  )
}
