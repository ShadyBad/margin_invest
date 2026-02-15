interface PercentileBarProps {
  value: number
  label?: string
  showValue?: boolean
  className?: string
}

export function PercentileBar({ value, label, showValue = true, className = "" }: PercentileBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value))

  const getColor = (v: number) => {
    if (v >= 90) return "bg-bullish"
    if (v >= 70) return "bg-accent"
    if (v >= 30) return "bg-text-secondary"
    return "bg-bearish"
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {label && (
        <span className="text-sm text-text-secondary w-40 shrink-0 truncate" title={label}>
          {label}
        </span>
      )}
      <div className="flex-1 h-2 bg-bg-primary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getColor(clampedValue)}`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showValue && (
        <span className="text-sm font-mono text-text-primary w-10 text-right">
          {clampedValue.toFixed(0)}
        </span>
      )}
    </div>
  )
}
