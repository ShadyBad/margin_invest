"use client"

import { useState } from "react"

export interface EquityCurvePoint {
  date: string // "2020-01-31"
  portfolioValue: number // cumulative value (start at 1.0)
  benchmarkValue: number // cumulative value (start at 1.0)
  drawdown: number // current drawdown from peak (0 to -1, e.g. -0.15)
}

export interface RegimeBand {
  startIndex: number // index into points array
  endIndex: number // index into points array
  regime: "bull" | "bear" | "sideways" | "crisis"
}

export interface EquityCurveProps {
  points: EquityCurvePoint[]
  regimeBands?: RegimeBand[]
  showDrawdown?: boolean // default true
  height?: number // default 400
  className?: string
}

// Chart layout constants
const CHART_WIDTH = 800
const CHART_HEIGHT = 400
const PADDING = { top: 20, right: 20, bottom: 50, left: 70 }
const PLOT_WIDTH = CHART_WIDTH - PADDING.left - PADDING.right
const PLOT_HEIGHT = CHART_HEIGHT - PADDING.top - PADDING.bottom

// Regime color mapping with opacity
const REGIME_COLORS: Record<RegimeBand["regime"], { color: string; opacity: number }> = {
  bull: { color: "var(--color-bullish)", opacity: 0.05 },
  bear: { color: "var(--color-bearish)", opacity: 0.08 },
  sideways: { color: "var(--color-warning)", opacity: 0.05 },
  crisis: { color: "var(--color-bearish)", opacity: 0.12 },
}

function formatDateLabel(dateStr: string): string {
  const parts = dateStr.split("-")
  if (parts.length >= 2) {
    return `${parts[0]}-${parts[1]}`
  }
  return dateStr
}

function formatPercent(value: number): string {
  const pct = (value - 1) * 100
  const sign = pct >= 0 ? "+" : ""
  return `${sign}${pct.toFixed(1)}%`
}

function formatDrawdownPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function selectXLabels(count: number, maxLabels: number): number[] {
  if (count <= maxLabels) {
    return Array.from({ length: count }, (_, i) => i)
  }

  const indices: number[] = [0]
  const step = (count - 1) / (maxLabels - 1)
  for (let i = 1; i < maxLabels - 1; i++) {
    indices.push(Math.round(step * i))
  }
  indices.push(count - 1)
  return indices
}

export function EquityCurve({
  points,
  regimeBands,
  showDrawdown = true,
  className,
}: EquityCurveProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (points.length === 0) {
    return (
      <div
        className={`terminal-card p-8 text-center ${className ?? ""}`}
        data-testid="equity-curve-empty"
      >
        <p className="text-text-secondary font-[family-name:var(--font-mono)]">
          No equity curve data available.
        </p>
      </div>
    )
  }

  // Compute Y-axis bounds from portfolio and benchmark values
  const allValues = points.flatMap((p) => [p.portfolioValue, p.benchmarkValue])
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const yPadding = Math.max((rawMax - rawMin) * 0.1, 0.01)
  const yMin = rawMin - yPadding
  const yMax = rawMax + yPadding

  // Scale functions
  const scaleX = (index: number): number => {
    if (points.length === 1) return PADDING.left + PLOT_WIDTH / 2
    return PADDING.left + (index / (points.length - 1)) * PLOT_WIDTH
  }

  const scaleY = (value: number): number => {
    return PADDING.top + PLOT_HEIGHT - ((value - yMin) / (yMax - yMin)) * PLOT_HEIGHT
  }

  // Build polyline points strings
  const portfolioPolyline = points
    .map((p, i) => `${scaleX(i)},${scaleY(p.portfolioValue)}`)
    .join(" ")

  const benchmarkPolyline = points
    .map((p, i) => `${scaleX(i)},${scaleY(p.benchmarkValue)}`)
    .join(" ")

  // Build drawdown area path (filled area between portfolio line and a zero-drawdown baseline)
  // Only render segments where drawdown < 0
  const hasDrawdown = showDrawdown && points.some((p) => p.drawdown < 0)
  let drawdownPath = ""
  if (hasDrawdown) {
    // We draw an area path: for each point, the top edge is the portfolio value,
    // and the bottom edge is the portfolio value adjusted for drawdown
    // (which means the peak value at that point = portfolioValue / (1 + drawdown) when drawdown < 0)
    // Simpler approach: shade between the portfolio line and the peak line.
    // Since drawdown = (current - peak) / peak, peak = current / (1 + drawdown)
    // But for visualization, we just shade the area from portfolio line down to
    // show the magnitude of drawdown. We'll draw the area below portfolio where drawdown < 0.

    // Build a path that traces the portfolio line for drawdown segments,
    // then returns along the "peak" line
    const pathParts: string[] = []
    let inDrawdown = false
    let segmentStart = -1

    for (let i = 0; i <= points.length; i++) {
      const isDD = i < points.length && points[i].drawdown < 0

      if (isDD && !inDrawdown) {
        // Start a new drawdown segment
        inDrawdown = true
        segmentStart = i
      } else if (!isDD && inDrawdown) {
        // End the drawdown segment - build a closed shape
        // Top edge: peak values (portfolioValue - drawdown * peak = portfolioValue / (1+drawdown))
        // Bottom edge: portfolio values
        const segmentPath: string[] = []

        // Move to the peak at segmentStart
        const startPeak = points[segmentStart].portfolioValue / (1 + points[segmentStart].drawdown)
        segmentPath.push(`M ${scaleX(segmentStart)},${scaleY(startPeak)}`)

        // Line along the peak for each point in segment
        for (let j = segmentStart; j < i; j++) {
          const peak = points[j].portfolioValue / (1 + points[j].drawdown)
          segmentPath.push(`L ${scaleX(j)},${scaleY(peak)}`)
        }

        // Line down to portfolio value at end of segment and back along portfolio line
        for (let j = i - 1; j >= segmentStart; j--) {
          segmentPath.push(`L ${scaleX(j)},${scaleY(points[j].portfolioValue)}`)
        }

        segmentPath.push("Z")
        pathParts.push(segmentPath.join(" "))
        inDrawdown = false
      }
    }

    drawdownPath = pathParts.join(" ")
  }

  // X-axis labels (~8 labels for 20-year chart)
  const xLabelIndices = selectXLabels(points.length, 8)

  // Y-axis gridlines (5 evenly spaced)
  const yGridCount = 5
  const yGridValues: number[] = []
  for (let i = 0; i <= yGridCount; i++) {
    yGridValues.push(yMin + (i / yGridCount) * (yMax - yMin))
  }

  return (
    <div className={`terminal-card relative ${className ?? ""}`}>
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="w-full h-auto"
        data-testid="equity-curve-chart"
        role="img"
        aria-label="Equity curve showing portfolio vs benchmark performance with regime bands"
      >
        {/* Regime background bands */}
        {regimeBands?.map((band, i) => {
          const x1 = scaleX(band.startIndex)
          const x2 = scaleX(band.endIndex)
          const { color, opacity } = REGIME_COLORS[band.regime]
          return (
            <rect
              key={`regime-${i}`}
              data-testid={`equity-curve-regime-band-${i}`}
              x={x1}
              y={PADDING.top}
              width={x2 - x1}
              height={PLOT_HEIGHT}
              fill={color}
              fillOpacity={opacity}
            />
          )
        })}

        {/* Gridlines */}
        {yGridValues.map((val, i) => (
          <g key={`grid-${i}`}>
            <line
              x1={PADDING.left}
              y1={scaleY(val)}
              x2={CHART_WIDTH - PADDING.right}
              y2={scaleY(val)}
              stroke="currentColor"
              className="text-border"
              strokeWidth={0.5}
              strokeDasharray="4 4"
            />
            <text
              x={PADDING.left - 8}
              y={scaleY(val) + 4}
              textAnchor="end"
              className="text-text-secondary font-[family-name:var(--font-mono)]"
              fill="currentColor"
              fontSize={11}
            >
              {formatPercent(val)}
            </text>
          </g>
        ))}

        {/* X-axis labels */}
        {xLabelIndices.map((idx) => (
          <text
            key={`x-label-${idx}`}
            x={scaleX(idx)}
            y={CHART_HEIGHT - PADDING.bottom + 20}
            textAnchor="middle"
            className="text-text-secondary font-[family-name:var(--font-mono)]"
            fill="currentColor"
            fontSize={11}
          >
            {formatDateLabel(points[idx].date)}
          </text>
        ))}

        {/* Axes */}
        <line
          x1={PADDING.left}
          y1={PADDING.top}
          x2={PADDING.left}
          y2={CHART_HEIGHT - PADDING.bottom}
          stroke="currentColor"
          className="text-border"
          strokeWidth={1}
        />
        <line
          x1={PADDING.left}
          y1={CHART_HEIGHT - PADDING.bottom}
          x2={CHART_WIDTH - PADDING.right}
          y2={CHART_HEIGHT - PADDING.bottom}
          stroke="currentColor"
          className="text-border"
          strokeWidth={1}
        />

        {/* Drawdown shading */}
        {hasDrawdown && drawdownPath && (
          <path
            d={drawdownPath}
            fill="var(--color-bearish)"
            fillOpacity={0.15}
            stroke="none"
            data-testid="equity-curve-drawdown-area"
          />
        )}

        {/* Benchmark line */}
        <polyline
          points={benchmarkPolyline}
          fill="none"
          stroke="currentColor"
          className="text-text-secondary"
          strokeWidth={1.5}
          data-testid="equity-curve-benchmark-line"
        />

        {/* Portfolio line */}
        <polyline
          points={portfolioPolyline}
          fill="none"
          stroke="currentColor"
          className="text-accent"
          strokeWidth={2.5}
          data-testid="equity-curve-portfolio-line"
        />

        {/* Tooltip hit areas */}
        {points.map((_, i) => {
          const hitWidth =
            points.length <= 1 ? PLOT_WIDTH : PLOT_WIDTH / (points.length - 1)
          const x = scaleX(i) - hitWidth / 2
          return (
            <rect
              key={`hit-${i}`}
              data-testid={`equity-curve-hit-${i}`}
              x={Math.max(PADDING.left, x)}
              y={PADDING.top}
              width={hitWidth}
              height={PLOT_HEIGHT}
              fill="transparent"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          )
        })}
      </svg>

      {/* Tooltip overlay */}
      {hoveredIndex !== null && (
        <div
          data-testid="equity-curve-tooltip"
          className="absolute bg-bg-elevated border border-border-primary rounded-sm px-3 py-2 shadow-lg pointer-events-none text-xs z-10"
          style={{
            left:
              scaleX(hoveredIndex) > CHART_WIDTH / 2
                ? `calc(${(scaleX(hoveredIndex) / CHART_WIDTH) * 100}% - 180px)`
                : `${(scaleX(hoveredIndex) / CHART_WIDTH) * 100}%`,
            top: `${(scaleY(points[hoveredIndex].portfolioValue) / CHART_HEIGHT) * 100}%`,
          }}
        >
          <div className="font-semibold text-text-primary mb-1 font-[family-name:var(--font-mono)]">
            {formatDateLabel(points[hoveredIndex].date)}
          </div>
          <div className="text-text-secondary">
            Portfolio: {formatPercent(points[hoveredIndex].portfolioValue)}
          </div>
          <div className="text-text-secondary">
            Benchmark: {formatPercent(points[hoveredIndex].benchmarkValue)}
          </div>
          <div
            className={
              points[hoveredIndex].portfolioValue >= points[hoveredIndex].benchmarkValue
                ? "text-bullish"
                : "text-bearish"
            }
          >
            Excess:{" "}
            {formatPercent(
              1 +
                (points[hoveredIndex].portfolioValue - points[hoveredIndex].benchmarkValue)
            ).replace("+", points[hoveredIndex].portfolioValue >= points[hoveredIndex].benchmarkValue ? "+" : "")}
          </div>
          {points[hoveredIndex].drawdown < 0 && (
            <div className="text-bearish">
              Drawdown: {formatDrawdownPercent(points[hoveredIndex].drawdown)}
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div
        className="flex items-center justify-center gap-6 mt-3 pb-4"
        data-testid="equity-curve-legend"
      >
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5 bg-accent rounded" />
          <span className="text-sm text-text-primary">Portfolio</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5 bg-text-secondary rounded" />
          <span className="text-sm text-text-primary">Benchmark</span>
        </div>
        {regimeBands && regimeBands.length > 0 && (
          <>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-sm bg-bullish opacity-30" />
              <span className="text-sm text-text-secondary">Bull</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-sm bg-bearish opacity-30" />
              <span className="text-sm text-text-secondary">Bear</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-sm bg-warning opacity-30" />
              <span className="text-sm text-text-secondary">Sideways</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
