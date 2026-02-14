import type { BacktestMetrics } from "@/lib/api/types"

interface MetricCardProps {
  label: string
  value: string
  colorClass: string
  testId: string
}

function MetricCard({ label, value, colorClass, testId }: MetricCardProps) {
  return (
    <div
      className="bg-bg-elevated border border-border-primary rounded-sm p-4"
      data-testid={testId}
    >
      <p className="text-xs text-text-secondary mb-1">{label}</p>
      <p className={`text-xl font-semibold ${colorClass}`}>{value}</p>
    </div>
  )
}

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

function excessColor(value: number): string {
  if (value > 0) return "text-accent"
  if (value < 0) return "text-bearish"
  return "text-text-primary"
}

function drawdownColor(value: number): string {
  return value > 0.3 ? "text-bearish" : "text-text-primary"
}

interface MetricsSummaryProps {
  metrics: BacktestMetrics
}

export function MetricsSummary({ metrics }: MetricsSummaryProps) {
  return (
    <div
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
      data-testid="metrics-summary"
    >
      <MetricCard
        label="CAGR"
        value={formatPercent(metrics.cagr)}
        colorClass={valueColor(metrics.cagr)}
        testId="metric-cagr"
      />
      <MetricCard
        label="Excess CAGR"
        value={formatPercent(metrics.excess_cagr)}
        colorClass={excessColor(metrics.excess_cagr)}
        testId="metric-excess-cagr"
      />
      <MetricCard
        label="Sharpe Ratio"
        value={formatRatio(metrics.sharpe_ratio)}
        colorClass={valueColor(metrics.sharpe_ratio)}
        testId="metric-sharpe-ratio"
      />
      <MetricCard
        label="Sortino Ratio"
        value={formatRatio(metrics.sortino_ratio)}
        colorClass={valueColor(metrics.sortino_ratio)}
        testId="metric-sortino-ratio"
      />
      <MetricCard
        label="Max Drawdown"
        value={formatPercent(metrics.max_drawdown)}
        colorClass={drawdownColor(metrics.max_drawdown)}
        testId="metric-max-drawdown"
      />
      <MetricCard
        label="Win Rate"
        value={formatPercent(metrics.win_rate)}
        colorClass="text-text-primary"
        testId="metric-win-rate"
      />
      <MetricCard
        label="Information Ratio"
        value={formatRatio(metrics.information_ratio)}
        colorClass={valueColor(metrics.information_ratio)}
        testId="metric-information-ratio"
      />
      <MetricCard
        label="Total Return"
        value={formatPercent(metrics.total_return)}
        colorClass={valueColor(metrics.total_return)}
        testId="metric-total-return"
      />
      <MetricCard
        label="Benchmark Return"
        value={formatPercent(metrics.benchmark_total_return)}
        colorClass="text-text-secondary"
        testId="metric-benchmark-return"
      />
      <MetricCard
        label="Months"
        value={String(metrics.num_months)}
        colorClass="text-text-primary"
        testId="metric-num-months"
      />
      <MetricCard
        label="Avg Turnover"
        value={formatPercent(metrics.avg_turnover)}
        colorClass="text-text-primary"
        testId="metric-avg-turnover"
      />
    </div>
  )
}
