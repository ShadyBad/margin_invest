import type { PriceBar } from "@/lib/api/types"

interface SparklineProps {
  bars: PriceBar[] | null | undefined
  buyPrice?: number | null
  sellPrice?: number | null
  width?: number
  height?: number
  className?: string
}

export function Sparkline({
  bars,
  buyPrice,
  sellPrice,
  width = 120,
  height = 32,
  className = "",
}: SparklineProps) {
  if (!bars || bars.length < 2) return null

  const closes = bars.map((b) => b.close)
  const min = closes.reduce((a, b) => Math.min(a, b))
  const max = closes.reduce((a, b) => Math.max(a, b))
  const range = max - min || 1
  const padding = 4

  const points = closes
    .map((c, i) => {
      const x = padding + (i / (closes.length - 1)) * (width - padding * 2)
      const y = padding + (1 - (c - min) / range) * (height - padding * 2)
      return `${x},${y}`
    })
    .join(" ")

  const lastClose = closes[closes.length - 1]
  let strokeColor = "text-text-secondary"
  if (buyPrice != null && lastClose <= buyPrice) strokeColor = "text-bullish"
  if (sellPrice != null && lastClose > sellPrice) strokeColor = "text-bearish"

  return (
    <svg
      width={width}
      height={height}
      className={className}
      data-testid="sparkline"
    >
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        points={points}
        className={strokeColor}
      />
    </svg>
  )
}
