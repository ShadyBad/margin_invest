"use client"

export type TimeRange = "1M" | "3M" | "6M" | "1Y" | "ALL"

const RANGES: TimeRange[] = ["1M", "3M", "6M", "1Y", "ALL"]

interface TimeRangeSelectorProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1" data-testid="time-range-selector">
      {RANGES.map((r) => (
        <button
          key={r}
          onClick={(e) => {
            e.stopPropagation()
            onChange(r)
          }}
          className={`px-2.5 py-1 text-xs font-mono tracking-wide rounded transition-colors ${
            value === r
              ? "bg-accent text-white"
              : "text-text-tertiary hover:text-text-secondary"
          }`}
        >
          {r}
        </button>
      ))}
    </div>
  )
}
