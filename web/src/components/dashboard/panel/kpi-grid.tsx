import { KpiCell } from "./kpi-cell"

interface KpiGridProps {
  sharpeRatio: number | null
  maxDrawdown: number | null
  volatility: number | null
  avgProfitMargin: number | null
  allocationWeight: number | null
  marginOfSafety: number | null
}

export function KpiGrid({
  sharpeRatio,
  maxDrawdown,
  volatility,
  avgProfitMargin,
  allocationWeight,
  marginOfSafety,
}: KpiGridProps) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-5" data-testid="kpi-grid">
      <KpiCell
        label="SHARPE RATIO"
        value={sharpeRatio != null ? sharpeRatio.toFixed(2) : "\u2014"}
        testId="kpi-sharpe-ratio-value"
      />
      <KpiCell
        label="MAX DRAWDOWN"
        value={maxDrawdown != null ? `${(maxDrawdown * 100).toFixed(1)}%` : "\u2014"}
        testId="kpi-max-drawdown-value"
      />
      <KpiCell
        label="VOLATILITY"
        value={volatility != null ? `${volatility.toFixed(1)}%` : "\u2014"}
        testId="kpi-volatility-value"
      />
      <KpiCell
        label="AVG PROFIT MARGIN"
        value={avgProfitMargin != null ? `${avgProfitMargin.toFixed(1)}%` : "\u2014"}
        testId="kpi-avg-profit-margin-value"
      />
      <KpiCell
        label="ALLOCATION"
        value={allocationWeight != null ? `${Math.round(allocationWeight)}%` : "\u2014"}
        testId="kpi-allocation-value"
      />
      <KpiCell
        label="MARGIN OF SAFETY"
        value={marginOfSafety != null ? `${Math.round(marginOfSafety)}%` : "\u2014"}
        testId="kpi-margin-of-safety-value"
      />
    </div>
  )
}
