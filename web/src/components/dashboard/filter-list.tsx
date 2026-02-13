import type { FilterResultResponse } from "@/lib/api/types"

interface FilterListProps {
  filters: FilterResultResponse[]
  className?: string
}

function FilterItem({ filter }: { filter: FilterResultResponse }) {
  return (
    <li
      className="flex items-start gap-2 text-sm"
      data-testid={`filter-${filter.name}`}
    >
      <span
        className={`shrink-0 mt-0.5 ${filter.passed ? "text-bullish" : "text-bearish"}`}
        aria-label={filter.passed ? "passed" : "failed"}
      >
        {filter.passed ? "\u2713" : "\u2717"}
      </span>
      <span className="text-text-primary">{filter.name}</span>
      {filter.reason && (
        <span className="text-text-secondary ml-auto text-xs">
          {filter.reason}
        </span>
      )}
    </li>
  )
}

export function FilterList({ filters, className = "" }: FilterListProps) {
  return (
    <div className={className} data-testid="filter-list">
      <h3 className="text-base font-semibold text-text-primary mb-3">
        Elimination Filters
      </h3>
      <ul className="space-y-2">
        {filters.map((filter) => (
          <FilterItem key={filter.name} filter={filter} />
        ))}
      </ul>
    </div>
  )
}
