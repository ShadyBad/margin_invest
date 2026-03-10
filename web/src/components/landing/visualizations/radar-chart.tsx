/**
 * RadarChart -- 5-axis radar/spider chart for scoring factor visualization.
 *
 * Renders a pentagon SVG with axis lines, a reference boundary polygon,
 * a filled data polygon, and labeled vertices.
 *
 * Used in: Pipeline (Step 10), Asset Detail (Step 16).
 */

interface RadarChartProps {
  factors: {
    quality: number // 0-100
    value: number
    momentum: number
    sentiment: number
    growth: number
  }
  size?: number // default 200
  className?: string
}

const FACTOR_KEYS = ["quality", "value", "momentum", "sentiment", "growth"] as const

const LABEL_OFFSET = 16 // px offset for labels from the outer vertex

/**
 * Compute vertex position for a regular pentagon.
 * Vertex i at angle (i * 72deg) measured clockwise from top.
 */
function vertex(cx: number, cy: number, radius: number, index: number): [number, number] {
  const angle = (index * 72 * Math.PI) / 180
  const x = cx + radius * Math.sin(angle)
  const y = cy - radius * Math.cos(angle)
  return [x, y]
}

function polygonPoints(cx: number, cy: number, radius: number, values?: number[]): string {
  return FACTOR_KEYS.map((_, i) => {
    const scale = values ? values[i] / 100 : 1
    const [x, y] = vertex(cx, cy, radius * scale, i)
    return `${x},${y}`
  }).join(" ")
}

export function RadarChart({
  factors,
  size = 200,
  className,
}: RadarChartProps) {
  const cx = size / 2
  const cy = size / 2
  const radius = size * 0.35 // Leave room for labels

  const values = FACTOR_KEYS.map((key) => Math.max(0, Math.min(100, factors[key])))

  const refPoints = polygonPoints(cx, cy, radius)
  const dataPoints = polygonPoints(cx, cy, radius, values)

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
    >
      {/* Axis lines from center to each vertex */}
      {FACTOR_KEYS.map((_, i) => {
        const [x, y] = vertex(cx, cy, radius, i)
        return (
          <line
            key={`axis-${i}`}
            x1={cx}
            y1={cy}
            x2={x}
            y2={y}
            stroke="currentColor"
            strokeOpacity={0.1}
            strokeWidth={1}
            data-axis-line=""
          />
        )
      })}

      {/* Reference pentagon (100% boundary) */}
      <polygon
        points={refPoints}
        fill="none"
        stroke="currentColor"
        strokeOpacity={0.15}
        strokeWidth={1}
        data-reference-polygon=""
      />

      {/* Data polygon (filled) */}
      <polygon
        points={dataPoints}
        fill="var(--color-accent, rgba(26, 122, 90, 0.15))"
        fillOpacity={0.15}
        stroke="var(--color-accent, #1A7A5A)"
        strokeWidth={1.5}
        data-data-polygon=""
      />

      {/* Data points (circles at each vertex) */}
      {FACTOR_KEYS.map((_, i) => {
        const [x, y] = vertex(cx, cy, radius * (values[i] / 100), i)
        return (
          <circle
            key={`point-${i}`}
            cx={x}
            cy={y}
            r={3}
            fill="var(--color-accent, #1A7A5A)"
            data-data-point=""
          />
        )
      })}

      {/* Labels at each vertex */}
      {FACTOR_KEYS.map((key, i) => {
        const [x, y] = vertex(cx, cy, radius + LABEL_OFFSET, i)
        return (
          <text
            key={`label-${key}`}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-text-tertiary"
            style={{
              fontSize: 10,
              fontFamily: "var(--font-mono, monospace)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {key}
          </text>
        )
      })}
    </svg>
  )
}
