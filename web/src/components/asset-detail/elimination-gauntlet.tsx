"use client"

import { useState } from "react"
import { FilterPill, FilterDetail } from "./filter-card"
import { formatEliminationPct } from "@/lib/format-elimination-pct"
import type { FilterResultResponse } from "@/lib/api/types"

interface EliminationGauntletProps {
  filters: FilterResultResponse[]
  eliminated: boolean
  totalScored?: number
  filtersSurvivedCount?: number
  sectorName?: string
}

export function EliminationGauntlet({ filters, eliminated, totalScored, filtersSurvivedCount, sectorName }: EliminationGauntletProps) {
  const [expandedFilter, setExpandedFilter] = useState<string | null>(null)

  const passCount = filters.filter((f) => f.passed).length
  const eliminatedPct = totalScored != null && filtersSurvivedCount != null && totalScored > 0
    ? formatEliminationPct(totalScored - filtersSurvivedCount, totalScored)
    : null

  // When eliminated, sort failed filters to top
  const sortedFilters = eliminated
    ? [...filters].sort((a, b) => {
        if (a.passed === b.passed) return 0
        return a.passed ? 1 : -1
      })
    : filters

  const allPassed = passCount === filters.length

  const expandedFilterData = expandedFilter != null
    ? sortedFilters.find((f) => f.name === expandedFilter) ?? null
    : null

  return (
    <section
      data-testid="elimination-gauntlet"
      className="rounded-lg p-6 space-y-4"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h2
            className="text-label-sm"
            style={{ color: "var(--color-on-surface-variant)" }}
          >
            ELIMINATION GAUNTLET
          </h2>
          <p
            className="text-body-md mt-1"
            style={{ color: "var(--color-on-surface-variant)" }}
          >
            Every scored stock must survive all six filters.
          </p>
          {eliminatedPct != null && (
            <p
              className="text-sm mt-0.5"
              style={{ color: "var(--color-on-surface-variant)" }}
            >
              {eliminatedPct}% of the universe was eliminated before scoring.
            </p>
          )}
        </div>
        <span
          className="text-sm px-2 py-1 rounded-sm"
          style={{
            fontFamily: "var(--font-data)",
            color: allPassed ? "var(--color-primary-muted)" : "var(--color-bearish)",
            background: allPassed
              ? "color-mix(in srgb, var(--color-primary-muted) 10%, transparent)"
              : "color-mix(in srgb, var(--color-bearish) 10%, transparent)",
          }}
        >
          {passCount} of {filters.length} passed
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {sortedFilters.map((filter) => (
          <FilterPill
            key={filter.name}
            filter={filter}
            isExpanded={expandedFilter === filter.name}
            onClick={() => setExpandedFilter(expandedFilter === filter.name ? null : filter.name)}
          />
        ))}
      </div>

      {expandedFilterData != null && (
        <FilterDetail filter={expandedFilterData} />
      )}

      {!eliminated && sectorName && (
        <p className="text-label-sm mt-6" style={{ color: "var(--color-text-tertiary)" }}>
          Sector-neutral ranking applied — {sectorName}
        </p>
      )}
    </section>
  )
}
