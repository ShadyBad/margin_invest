interface ScoreDeltaProps {
  current: number
  previous: number | null
}

export function ScoreDelta({ current, previous }: ScoreDeltaProps) {
  if (previous == null) return null
  const delta = Math.round(current) - Math.round(previous)
  if (delta === 0) return null
  const isPositive = delta > 0

  return (
    <span
      data-testid="score-delta"
      className={`text-sm font-mono font-medium ${isPositive ? "text-bullish" : "text-warning"}`}
    >
      {isPositive ? "\u25B2" : "\u25BC"}{isPositive ? `+${delta}` : delta}
    </span>
  )
}
