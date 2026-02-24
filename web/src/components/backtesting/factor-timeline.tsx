import { useMemo } from "react"

export interface FactorAvailabilityEntry {
  date: string
  factors: string[]
}

export interface FactorTimelineProps {
  entries: FactorAvailabilityEntry[]
  allFactors?: string[]
}

function formatDateLabel(dateStr: string): string {
  const [year, month] = dateStr.split("-")
  const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ]
  const monthIndex = parseInt(month, 10) - 1
  return `${monthNames[monthIndex]} ${year}`
}

function pickDateLabels(dates: string[], maxLabels: number): string[] {
  if (dates.length <= maxLabels) return dates
  const labels: string[] = []
  for (let i = 0; i < maxLabels; i++) {
    const index = Math.round((i / (maxLabels - 1)) * (dates.length - 1))
    labels.push(dates[index])
  }
  return labels
}

const ROW_HEIGHT = 24
const LABEL_WIDTH = 120
const PADDING_RIGHT = 16
const AXIS_HEIGHT = 28

export function FactorTimeline({ entries, allFactors }: FactorTimelineProps) {
  const derivedFactors = useMemo(() => {
    if (allFactors && allFactors.length > 0) return allFactors
    const factorSet = new Set<string>()
    for (const entry of entries) {
      for (const factor of entry.factors) {
        factorSet.add(factor)
      }
    }
    return Array.from(factorSet)
  }, [entries, allFactors])

  const dates = useMemo(() => entries.map((e) => e.date), [entries])
  const dateLabels = useMemo(() => pickDateLabels(dates, 6), [dates])

  if (entries.length === 0) {
    return (
      <div className="terminal-card p-6" data-testid="factor-timeline">
        <h3 className="text-xs uppercase tracking-wider text-text-secondary mb-4">
          Factor Availability
        </h3>
        <p className="text-sm text-text-tertiary">No factor data available</p>
      </div>
    )
  }

  const chartHeight = derivedFactors.length * ROW_HEIGHT + AXIS_HEIGHT
  const numEntries = entries.length

  return (
    <div className="terminal-card p-6" data-testid="factor-timeline">
      <h3 className="text-xs uppercase tracking-wider text-text-secondary mb-4">
        Factor Availability
      </h3>
      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 800 ${chartHeight}`}
          className="w-full"
          preserveAspectRatio="xMinYMin meet"
          role="img"
          aria-label="Factor availability timeline"
        >
          {/* Factor rows */}
          {derivedFactors.map((factor, rowIndex) => {
            const y = rowIndex * ROW_HEIGHT
            return (
              <g key={factor} data-testid={`factor-row-${factor}`}>
                {/* Factor label */}
                <text
                  x={LABEL_WIDTH - 8}
                  y={y + ROW_HEIGHT / 2 + 4}
                  textAnchor="end"
                  className="fill-current text-text-secondary"
                  style={{
                    fontSize: "12px",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {factor}
                </text>

                {/* Timeline segments */}
                {entries.map((entry, entryIndex) => {
                  const barWidth =
                    (800 - LABEL_WIDTH - PADDING_RIGHT) / numEntries
                  const x = LABEL_WIDTH + entryIndex * barWidth
                  const isActive = entry.factors.includes(factor)

                  return (
                    <rect
                      key={entry.date}
                      x={x}
                      y={y + 2}
                      width={barWidth - 1}
                      height={ROW_HEIGHT - 4}
                      rx={2}
                      fill={isActive ? "var(--color-accent)" : "transparent"}
                      opacity={isActive ? 0.6 : 0}
                      stroke={isActive ? "none" : "var(--color-border)"}
                      strokeWidth={isActive ? 0 : 0.5}
                      strokeOpacity={0.3}
                    />
                  )
                })}

                {/* Row separator line */}
                {rowIndex < derivedFactors.length - 1 && (
                  <line
                    x1={LABEL_WIDTH}
                    y1={y + ROW_HEIGHT}
                    x2={800 - PADDING_RIGHT}
                    y2={y + ROW_HEIGHT}
                    stroke="var(--color-border)"
                    strokeOpacity={0.2}
                  />
                )}
              </g>
            )
          })}

          {/* X-axis date labels */}
          {dateLabels.map((dateStr) => {
            const dateIndex = dates.indexOf(dateStr)
            const barWidth =
              (800 - LABEL_WIDTH - PADDING_RIGHT) / numEntries
            const x = LABEL_WIDTH + dateIndex * barWidth + barWidth / 2

            return (
              <text
                key={dateStr}
                x={x}
                y={derivedFactors.length * ROW_HEIGHT + 18}
                textAnchor="middle"
                className="fill-current text-text-tertiary"
                style={{
                  fontSize: "10px",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {formatDateLabel(dateStr)}
              </text>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
