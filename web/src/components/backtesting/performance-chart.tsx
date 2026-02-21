interface SnapshotData {
  date: string
  portfolio_value: number
  benchmark_value: number
  portfolio_return: number
  benchmark_return: number
}

interface PerformanceChartProps {
  snapshots: SnapshotData[]
  portfolioLabel?: string
  benchmarkLabel?: string
  className?: string
}

// Chart layout constants
const CHART_WIDTH = 800
const CHART_HEIGHT = 400
const PADDING = { top: 20, right: 20, bottom: 50, left: 70 }
const PLOT_WIDTH = CHART_WIDTH - PADDING.left - PADDING.right
const PLOT_HEIGHT = CHART_HEIGHT - PADDING.top - PADDING.bottom

function computeCumulativeReturns(returns: number[]): number[] {
  const cumulative: number[] = []
  let value = 1
  for (const r of returns) {
    value *= 1 + r
    cumulative.push(value - 1) // store as cumulative % return
  }
  return cumulative
}

function formatDateLabel(dateStr: string): string {
  const parts = dateStr.split("-")
  if (parts.length >= 2) {
    return `${parts[0]}-${parts[1]}`
  }
  return dateStr
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function selectXLabels(dates: string[], maxLabels: number): number[] {
  if (dates.length <= maxLabels) {
    return dates.map((_, i) => i)
  }

  const indices: number[] = [0] // always include first
  const step = (dates.length - 1) / (maxLabels - 1)
  for (let i = 1; i < maxLabels - 1; i++) {
    indices.push(Math.round(step * i))
  }
  indices.push(dates.length - 1) // always include last
  return indices
}

export function PerformanceChart({
  snapshots,
  portfolioLabel = "Portfolio",
  benchmarkLabel = "Benchmark",
  className,
}: PerformanceChartProps) {
  if (snapshots.length === 0) {
    return (
      <div
        className={`bg-bg-elevated border border-border-primary rounded-sm p-8 text-center ${className ?? ""}`}
        data-testid="performance-chart-empty"
      >
        <p className="text-text-secondary">No chart data available.</p>
      </div>
    )
  }

  const portfolioReturns = snapshots.map((s) => s.portfolio_return)
  const benchmarkReturns = snapshots.map((s) => s.benchmark_return)

  const portfolioCumulative = computeCumulativeReturns(portfolioReturns)
  const benchmarkCumulative = computeCumulativeReturns(benchmarkReturns)

  // Compute Y-axis bounds
  const allValues = [...portfolioCumulative, ...benchmarkCumulative]
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const yPadding = Math.max((rawMax - rawMin) * 0.1, 0.01)
  const yMin = rawMin - yPadding
  const yMax = rawMax + yPadding

  // Scale functions
  const scaleX = (index: number): number => {
    if (snapshots.length === 1) return PADDING.left + PLOT_WIDTH / 2
    return PADDING.left + (index / (snapshots.length - 1)) * PLOT_WIDTH
  }

  const scaleY = (value: number): number => {
    return PADDING.top + PLOT_HEIGHT - ((value - yMin) / (yMax - yMin)) * PLOT_HEIGHT
  }

  // Build polyline points
  const portfolioPoints = portfolioCumulative
    .map((v, i) => `${scaleX(i)},${scaleY(v)}`)
    .join(" ")

  const benchmarkPoints = benchmarkCumulative
    .map((v, i) => `${scaleX(i)},${scaleY(v)}`)
    .join(" ")

  // X-axis labels
  const dates = snapshots.map((s) => s.date)
  const xLabelIndices = selectXLabels(dates, 5)

  // Y-axis gridlines (5 evenly spaced)
  const yGridCount = 5
  const yGridValues: number[] = []
  for (let i = 0; i <= yGridCount; i++) {
    yGridValues.push(yMin + (i / yGridCount) * (yMax - yMin))
  }

  return (
    <div className={className ?? ""}>
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="w-full h-auto"
        data-testid="performance-chart"
        role="img"
        aria-label="Performance chart showing portfolio vs benchmark returns"
      >
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
              className="text-text-secondary"
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
            className="text-text-secondary"
            fill="currentColor"
            fontSize={11}
          >
            {formatDateLabel(dates[idx])}
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

        {/* Benchmark line */}
        <polyline
          points={benchmarkPoints}
          fill="none"
          stroke="currentColor"
          className="text-text-secondary"
          strokeWidth={2}
          data-testid="benchmark-line"
        />

        {/* Portfolio line */}
        <polyline
          points={portfolioPoints}
          fill="none"
          stroke="currentColor"
          className="text-accent"
          strokeWidth={2.5}
          data-testid="portfolio-line"
        />
      </svg>

      {/* Legend */}
      <div
        className="flex items-center justify-center gap-6 mt-3"
        data-testid="chart-legend"
      >
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5 bg-accent rounded" />
          <span className="text-sm text-text-primary">{portfolioLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5 bg-text-secondary rounded" />
          <span className="text-sm text-text-primary">{benchmarkLabel}</span>
        </div>
      </div>
    </div>
  )
}
