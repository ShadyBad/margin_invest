import { formatAttributeLabel } from "@/lib/format"
import type { FilterResultResponse } from "@/lib/api/types"

interface FilterListProps {
  filters: FilterResultResponse[]
  className?: string
}

function FilterItem({ filter }: { filter: FilterResultResponse }) {
  const isInconclusive = filter.verdict === "inconclusive"
  const icon = isInconclusive ? "?" : filter.passed ? "\u2713" : "\u2717"
  const iconColor = isInconclusive
    ? "text-amber-500"
    : filter.passed
      ? "text-bullish"
      : "text-bearish"
  const label = isInconclusive ? "inconclusive" : filter.passed ? "passed" : "failed"
  const labelColor = isInconclusive ? "text-amber-500/70" : "text-text-tertiary"

  return (
    <li
      className="flex items-start gap-2 text-sm"
      data-testid={`filter-${filter.name}`}
    >
      <span
        className={`shrink-0 mt-0.5 ${iconColor}`}
        aria-label={label}
      >
        {icon}
      </span>
      <span className="text-text-primary">{formatAttributeLabel(filter.name)}</span>
      <span className={`text-xs font-mono ml-auto ${labelColor}`}>{label}</span>
    </li>
  )
}

export function FilterList({ filters, className = "" }: FilterListProps) {
  return (
    <div className={className} data-testid="filter-list">
      <h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
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
