interface MarketRegimeLabelProps {
  pickCount: number
}

function getRegime(count: number): { label: string; color: string } {
  if (count <= 1)
    return { label: "Overheated", color: "text-bearish bg-bearish/10 border-bearish/20" }
  if (count <= 5)
    return { label: "Concentrated", color: "text-warning bg-warning/10 border-warning/20" }
  return { label: "Normal", color: "text-text-tertiary bg-white/[0.03] border-white/[0.06]" }
}

export function MarketRegimeLabel({ pickCount }: MarketRegimeLabelProps) {
  const regime = getRegime(pickCount)
  return (
    <span
      className={`text-xs font-mono px-2 py-0.5 rounded border ${regime.color}`}
      data-testid="market-regime"
    >
      {regime.label}
    </span>
  )
}
