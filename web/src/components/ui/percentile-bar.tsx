interface PercentileBarProps {
  value: number
  label?: string
  showValue?: boolean
  className?: string
}

export function PercentileBar({ value, label, showValue = true, className = "" }: PercentileBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value))

  const getColor = (v: number) => {
    if (v >= 90) return "bg-percentile-exceptional"
    if (v >= 70) return "bg-percentile-strong"
    if (v >= 50) return "bg-percentile-average"
    if (v >= 30) return "bg-percentile-below"
    return "bg-percentile-weak"
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {label && (
        <span className="text-xs text-text-tertiary w-40 shrink-0 truncate uppercase tracking-[0.1em]" title={label}>
          {label}
        </span>
      )}
      <div className="flex-1 h-[8px] bg-bg-primary rounded-full overflow-hidden shadow-[inset_0_1px_2px_rgba(0,0,0,0.1)]">
        <div
          className={`h-full rounded-r-full transition-[width] duration-[600ms] delay-200 ease-[cubic-bezier(0.22,1,0.36,1)] ${getColor(clampedValue)}`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showValue && (
        <span className="text-sm font-mono text-text-primary w-10 text-right tabular-nums">
          {clampedValue.toFixed(0)}
        </span>
      )}
    </div>
  )
}
