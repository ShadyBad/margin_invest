interface MonthlyReturn {
  date: string // YYYY-MM-DD
  portfolio_return: number
  benchmark_return: number
}

interface ReturnsHeatmapProps {
  returns: MonthlyReturn[]
  className?: string
}

const MONTH_ABBRS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
]

function excessReturnColor(excess: number): string {
  const pct = excess * 100
  if (pct > 2) return "bg-bullish/80 text-white"
  if (pct > 0) return "bg-bullish/30 text-text-primary"
  if (pct > -2) return "bg-bearish/30 text-text-primary"
  return "bg-bearish/80 text-white"
}

function formatExcess(excess: number): string {
  return `${(excess * 100).toFixed(1)}%`
}

export function ReturnsHeatmap({ returns, className }: ReturnsHeatmapProps) {
  if (returns.length === 0) {
    return (
      <div data-testid="returns-heatmap" className={className}>
        <p className="text-text-secondary text-sm">No return data available.</p>
      </div>
    )
  }

  // Build a map: year -> month (0-11) -> excess return
  const dataMap = new Map<number, Map<number, number>>()

  for (const r of returns) {
    const d = new Date(r.date)
    const year = d.getUTCFullYear()
    const month = d.getUTCMonth()
    const excess = r.portfolio_return - r.benchmark_return

    if (!dataMap.has(year)) {
      dataMap.set(year, new Map())
    }
    dataMap.get(year)!.set(month, excess)
  }

  const years = Array.from(dataMap.keys()).sort((a, b) => a - b)

  return (
    <div
      data-testid="returns-heatmap"
      className={className}
      role="table"
      aria-label="Monthly excess returns heatmap"
    >
      {/* Month header row */}
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: "60px repeat(12, 1fr)" }}
        role="row"
      >
        <div role="columnheader" className="text-xs text-text-secondary" />
        {MONTH_ABBRS.map((m) => (
          <div
            key={m}
            role="columnheader"
            className="text-xs text-text-secondary text-center font-medium py-1"
          >
            {m}
          </div>
        ))}
      </div>

      {/* Data rows */}
      {years.map((year) => {
        const monthData = dataMap.get(year)!
        return (
          <div
            key={year}
            className="grid gap-1"
            style={{ gridTemplateColumns: "60px repeat(12, 1fr)" }}
            role="row"
          >
            <div
              role="rowheader"
              className="text-xs text-text-secondary flex items-center font-medium"
            >
              {year}
            </div>
            {Array.from({ length: 12 }, (_, monthIdx) => {
              const excess = monthData.get(monthIdx)
              const monthStr = String(monthIdx + 1).padStart(2, "0")
              const cellKey = `${year}-${monthStr}`

              if (excess === undefined) {
                return (
                  <div
                    key={cellKey}
                    data-testid={`heatmap-cell-${cellKey}`}
                    role="cell"
                    className="rounded text-center text-xs py-2 bg-bg-secondary border border-border"
                  />
                )
              }

              return (
                <div
                  key={cellKey}
                  data-testid={`heatmap-cell-${cellKey}`}
                  role="cell"
                  className={`rounded text-center text-xs py-2 font-medium ${excessReturnColor(excess)}`}
                >
                  {formatExcess(excess)}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
