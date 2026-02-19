import { KpiCell } from "./kpi-cell"

interface KpiGridProps {
  sharpeRatio: number | null
  maxDrawdown: number | null
  volatility: number | null
  avgProfitMargin: number | null
  allocationWeight: number | null
  scoreDelta: number | null
}

export function KpiGrid({
  sharpeRatio,
  maxDrawdown,
  volatility,
  avgProfitMargin,
  allocationWeight,
  scoreDelta,
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
        label="SCORE DELTA"
        value={scoreDelta != null ? `${scoreDelta > 0 ? "+" : ""}${scoreDelta.toFixed(1)}` : "\u2014"}
        color={scoreDelta != null ? (scoreDelta >= 0 ? "text-emerald-400" : "text-red-400") : undefined}
        unavailableReason={scoreDelta == null ? "First scoring run" : undefined}
        testId="kpi-score-delta-value"
      />
    </div>
  )
}
