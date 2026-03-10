/**
 * Sparkline -- Minimal SVG line chart for inline data trends.
 *
 * Renders a polyline with optional gradient fill beneath it.
 * All values are normalized to fit within the given dimensions.
 *
 * Used in: Results Stage (Step 11), Asset Detail (Step 16).
 */

interface SparklineProps {
  data: number[]
  width?: number // default 120
  height?: number // default 48
  color?: string // default "var(--color-accent)"
  className?: string
}

const PADDING = 2 // px padding so the stroke isn't clipped at edges

export function Sparkline({
  data,
  width = 120,
  height = 48,
  color = "var(--color-accent)",
  className,
}: SparklineProps) {
  if (data.length === 0) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        className={className}
        aria-hidden="true"
      />
    )
  }

  const gradientId = `sparkline-grad-${width}-${height}-${data.length}`

  // Compute normalized points
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1 // avoid division by zero for flat data

  const usableHeight = height - PADDING * 2
  const usableWidth = width - PADDING * 2

  const points = data.map((value, i) => {
    const x =
      data.length === 1
        ? width / 2
        : PADDING + (i / (data.length - 1)) * usableWidth
    const y =
      PADDING + usableHeight - ((value - min) / range) * usableHeight
    return `${x},${y}`
  })

  const pointsStr = points.join(" ")

  // Build the fill polygon: line points + bottom-right + bottom-left
  const firstX = data.length === 1 ? width / 2 : PADDING
  const lastX =
    data.length === 1
      ? width / 2
      : PADDING + usableWidth
  const fillPoints = `${pointsStr} ${lastX},${height - PADDING} ${firstX},${height - PADDING}`

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.15} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Gradient fill area */}
      <polygon
        points={fillPoints}
        fill={`url(#${gradientId})`}
      />

      {/* Data line */}
      <polyline
        points={pointsStr}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
