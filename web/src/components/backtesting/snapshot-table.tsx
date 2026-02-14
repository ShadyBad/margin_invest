interface SnapshotRow {
  date: string
  portfolio_value: number
  benchmark_value: number
  portfolio_return: number
  benchmark_return: number
  turnover: number
  transaction_costs: number
}

interface SnapshotTableProps {
  snapshots: SnapshotRow[]
  className?: string
}

function formatCurrency(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function excessColor(excess: number): string {
  if (excess > 0) return "text-bullish"
  if (excess < 0) return "text-bearish"
  return "text-text-primary"
}

function rowTestId(date: string): string {
  // Extract YYYY-MM from date string (YYYY-MM-DD)
  return `snapshot-row-${date.slice(0, 7)}`
}

const COLUMNS = [
  "Date",
  "Portfolio Value",
  "Benchmark Value",
  "Portfolio Return",
  "Benchmark Return",
  "Excess Return",
  "Turnover",
  "Transaction Costs",
] as const

export function SnapshotTable({ snapshots, className }: SnapshotTableProps) {
  if (snapshots.length === 0) {
    return (
      <div data-testid="snapshot-table" className={className}>
        <p className="text-text-secondary text-sm">
          No snapshot data available.
        </p>
      </div>
    )
  }

  return (
    <div
      data-testid="snapshot-table"
      className={`overflow-auto max-h-[600px] ${className ?? ""}`}
    >
      <table
        className="w-full text-sm border-collapse"
        aria-label="Backtest snapshot data"
      >
        <thead className="sticky top-0 bg-bg-primary z-10">
          <tr className="border-b border-border-primary">
            {COLUMNS.map((col) => (
              <th
                key={col}
                scope="col"
                className="text-left text-xs text-text-secondary font-medium px-3 py-2 whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {snapshots.map((snap) => {
            const excess = snap.portfolio_return - snap.benchmark_return
            return (
              <tr
                key={snap.date}
                data-testid={rowTestId(snap.date)}
                className="border-b border-border-primary hover:bg-bg-elevated transition-colors"
              >
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {snap.date}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {formatCurrency(snap.portfolio_value)}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {formatCurrency(snap.benchmark_value)}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {formatPercent(snap.portfolio_return)}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {formatPercent(snap.benchmark_return)}
                </td>
                <td
                  className={`px-3 py-2 whitespace-nowrap font-medium ${excessColor(excess)}`}
                >
                  {formatPercent(excess)}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  {formatPercent(snap.turnover)}
                </td>
                <td className="px-3 py-2 text-text-primary whitespace-nowrap">
                  ${formatCurrency(snap.transaction_costs)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
