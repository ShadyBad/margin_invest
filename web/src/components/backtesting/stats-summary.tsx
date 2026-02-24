interface BacktestStats {
  cagr: number
  excessCagr: number
  sharpe: number
  sortino: number
  maxDrawdown: number
  winRate: number
  informationRatio: number
  totalReturn: number
  benchmarkReturn: number
  numMonths: number
  avgTurnover: number
  calmarRatio?: number
}

interface StatsSummaryProps {
  stats: BacktestStats
}

type StatDef = {
  key: string
  label: string
  format: "percent" | "ratio" | "integer"
  field: keyof BacktestStats
  optional?: boolean
}

const STAT_DEFS: StatDef[] = [
  { key: "cagr", label: "CAGR", format: "percent", field: "cagr" },
  { key: "excessCagr", label: "Excess CAGR", format: "percent", field: "excessCagr" },
  { key: "sharpe", label: "Sharpe Ratio", format: "ratio", field: "sharpe" },
  { key: "sortino", label: "Sortino Ratio", format: "ratio", field: "sortino" },
  { key: "maxDrawdown", label: "Max Drawdown", format: "percent", field: "maxDrawdown" },
  { key: "winRate", label: "Win Rate", format: "percent", field: "winRate" },
  { key: "informationRatio", label: "Information Ratio", format: "ratio", field: "informationRatio" },
  { key: "totalReturn", label: "Total Return", format: "percent", field: "totalReturn" },
  { key: "benchmarkReturn", label: "Benchmark Return", format: "percent", field: "benchmarkReturn" },
  { key: "numMonths", label: "Months", format: "integer", field: "numMonths" },
  { key: "avgTurnover", label: "Avg Turnover", format: "percent", field: "avgTurnover" },
  { key: "calmarRatio", label: "Calmar Ratio", format: "ratio", field: "calmarRatio", optional: true },
]

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatRatio(value: number): string {
  return value.toFixed(2)
}

function valueColor(value: number): string {
  if (value > 0) return "text-bullish"
  if (value < 0) return "text-bearish"
  return "text-text-primary"
}

export function StatsSummary({ stats }: StatsSummaryProps) {
  const visibleStats = STAT_DEFS.filter(
    (def) => !def.optional || stats[def.field] !== undefined
  )

  return (
    <div className="terminal-card p-6" data-testid="stats-summary">
      <h3 className="text-xs font-semibold tracking-widest text-text-secondary mb-4">
        PERFORMANCE STATISTICS
      </h3>

      <div className="grid grid-cols-2 gap-x-8 gap-y-3">
        {visibleStats.map((def) => {
          const rawValue = stats[def.field]
          const value = rawValue as number

          let formatted: string
          if (def.format === "percent") {
            formatted = formatPercent(value)
          } else if (def.format === "ratio") {
            formatted = formatRatio(value)
          } else {
            formatted = String(value)
          }

          return (
            <div key={def.key} className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">{def.label}</span>
              <span
                data-testid={`stat-${def.key}`}
                className={`font-[family-name:var(--font-mono)] text-sm ${valueColor(value)}`}
              >
                {formatted}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
