interface SectorMicroBarProps {
  percentile: number
}

function getFillColor(percentile: number): string {
  if (percentile >= 90) return "bg-[var(--color-percentile-exceptional)]"
  if (percentile >= 70) return "bg-[var(--color-percentile-strong)]"
  if (percentile >= 40) return "bg-[var(--color-percentile-average)]"
  if (percentile >= 20) return "bg-[var(--color-percentile-below)]"
  return "bg-[var(--color-percentile-weak)]"
}

export function SectorMicroBar({ percentile }: SectorMicroBarProps) {
  return (
    <div data-testid="sector-micro-bar" className="mt-1 mb-0.5">
      <div className="relative h-1 bg-white/[0.04] rounded-full overflow-visible">
        {/* Sector median (P50) marker */}
        <div
          data-testid="median-marker"
          className="absolute top-[-1px] h-[6px] w-px bg-white/25"
          style={{ left: "50%" }}
        />

        {/* P90 marker */}
        <div
          data-testid="p90-marker"
          className="absolute top-[-1px] h-[6px] w-px bg-white/15"
          style={{ left: "90%" }}
        />

        {/* Fill bar */}
        <div
          data-testid="percentile-fill"
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-500 opacity-60 ${getFillColor(percentile)}`}
          style={{ width: `${percentile}%` }}
        />

        {/* Stock position dot */}
        <div
          data-testid="stock-position"
          className="absolute top-[-2px] w-1.5 h-1.5 rounded-full bg-accent border border-accent/60"
          style={{ left: `${percentile}%`, transform: "translateX(-50%)" }}
        />
      </div>
    </div>
  )
}
