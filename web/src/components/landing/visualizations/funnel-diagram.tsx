/**
 * FunnelDiagram -- Vertical SVG funnel showing pipeline narrowing stages.
 *
 * 4 horizontal bars that narrow from top to bottom, connected by angled sides.
 * Each bar labeled with stage name and count.
 *
 * Used in: Pipeline section (Step 10).
 */

interface FunnelDiagramProps {
  universeCount: number
  eligibleCount: number
  scoredCount: number
  survivingCount: number
  className?: string
}

interface FunnelStage {
  label: string
  count: number
  widthPct: number
  opacity: number
}

function formatCount(n: number): string {
  return n.toLocaleString("en-US")
}

const SVG_WIDTH = 280
const SVG_HEIGHT = 260
const BAR_HEIGHT = 36
const BAR_GAP = 16
const CONNECTOR_HEIGHT = 12
const START_Y = 16

export function FunnelDiagram({
  universeCount,
  eligibleCount,
  scoredCount,
  survivingCount,
  className,
}: FunnelDiagramProps) {
  const stages: FunnelStage[] = [
    { label: "Universe", count: universeCount, widthPct: 1.0, opacity: 1.0 },
    { label: "Eligible", count: eligibleCount, widthPct: 0.7, opacity: 0.8 },
    { label: "Scored", count: scoredCount, widthPct: 0.5, opacity: 0.6 },
    { label: "Survivors", count: survivingCount, widthPct: 0.2, opacity: 0.4 },
  ]

  const maxBarWidth = SVG_WIDTH - 40 // 20px padding each side
  const centerX = SVG_WIDTH / 2

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
      width={SVG_WIDTH}
      height={SVG_HEIGHT}
      className={className}
      aria-label="Pipeline funnel diagram"
      role="img"
    >
      {stages.map((stage, i) => {
        const barWidth = maxBarWidth * stage.widthPct
        const y = START_Y + i * (BAR_HEIGHT + CONNECTOR_HEIGHT + BAR_GAP)
        const x = centerX - barWidth / 2

        // Connector trapezoid between this bar and the next
        const nextStage = stages[i + 1]

        return (
          <g key={stage.label} data-funnel-stage={stage.label}>
            {/* Bar rectangle */}
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={BAR_HEIGHT}
              rx={4}
              fill="var(--color-accent, #1A7A5A)"
              fillOpacity={stage.opacity}
            />

            {/* Stage label (left-aligned inside bar) */}
            <text
              x={centerX}
              y={y + BAR_HEIGHT / 2 - 6}
              textAnchor="middle"
              className="fill-text-primary"
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono, monospace)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              {stage.label}
            </text>

            {/* Count (centered, below label) */}
            <text
              x={centerX}
              y={y + BAR_HEIGHT / 2 + 8}
              textAnchor="middle"
              className="fill-text-primary"
              style={{
                fontSize: 13,
                fontFamily: "var(--font-mono, monospace)",
                fontWeight: 600,
              }}
            >
              {formatCount(stage.count)}
            </text>

            {/* Connector to next stage */}
            {nextStage && (() => {
              const nextBarWidth = maxBarWidth * nextStage.widthPct
              const connectorTopY = y + BAR_HEIGHT
              const connectorBottomY = connectorTopY + CONNECTOR_HEIGHT + BAR_GAP

              const topLeft = centerX - barWidth / 2
              const topRight = centerX + barWidth / 2
              const bottomLeft = centerX - nextBarWidth / 2
              const bottomRight = centerX + nextBarWidth / 2

              return (
                <polygon
                  points={`${topLeft},${connectorTopY} ${topRight},${connectorTopY} ${bottomRight},${connectorBottomY} ${bottomLeft},${connectorBottomY}`}
                  fill="var(--color-accent, #1A7A5A)"
                  fillOpacity={0.08}
                  data-funnel-connector=""
                />
              )
            })()}
          </g>
        )
      })}
    </svg>
  )
}
