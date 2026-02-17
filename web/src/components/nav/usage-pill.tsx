interface UsagePillProps {
  used: number
  limit: number | null
  className?: string
}

export function UsagePill({ used, limit, className = "" }: UsagePillProps) {
  if (limit == null) return null

  const atLimit = used >= limit

  return (
    <span
      className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
        atLimit
          ? "bg-warning/10 text-warning"
          : "bg-accent/10 text-accent"
      } ${className}`}
      data-testid="usage-pill"
      title={atLimit
        ? `All ${limit} analyses used this month`
        : `${limit - used} analyses remaining this month`
      }
    >
      {used}/{limit}
    </span>
  )
}
