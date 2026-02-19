import { KpiCell } from "./kpi-cell"

interface KpiGridProps {
  sharpeRatio: number | null
  sharpeRatioUnavailable?: string | null
  maxDrawdown: number | null
  maxDrawdownUnavailable?: string | null
  volatility: number | null
  volatilityUnavailable?: string | null
  avgProfitMargin: number | null
  avgProfitMarginUnavailable?: string | null
  scoreDelta: number | null
  delta: number | null
  deltaUnavailable?: string | null
}

export function KpiGrid({
  sharpeRatio,
  sharpeRatioUnavailable,
  maxDrawdown,
  maxDrawdownUnavailable,
  volatility,
  volatilityUnavailable,
  avgProfitMargin,
  avgProfitMarginUnavailable,
  scoreDelta,
  delta,
  deltaUnavailable,
}: KpiGridProps) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-5" data-testid="kpi-grid">
      <KpiCell
        label="SHARPE RATIO"
        value={sharpeRatio != null ? sharpeRatio.toFixed(2) : "\u2014"}
        unavailableReason={sharpeRatio == null ? (sharpeRatioUnavailable ?? undefined) : undefined}
        testId="kpi-sharpe-ratio-value"
      />
      <KpiCell
        label="MAX DRAWDOWN"
        value={maxDrawdown != null ? `${(maxDrawdown * 100).toFixed(1)}%` : "\u2014"}
        unavailableReason={maxDrawdown == null ? (maxDrawdownUnavailable ?? undefined) : undefined}
        testId="kpi-max-drawdown-value"
      />
      <KpiCell
        label="VOLATILITY"
        value={volatility != null ? `${volatility.toFixed(1)}%` : "\u2014"}
        unavailableReason={volatility == null ? (volatilityUnavailable ?? undefined) : undefined}
        testId="kpi-volatility-value"
      />
      <KpiCell
        label="AVG PROFIT MARGIN"
        value={avgProfitMargin != null ? `${avgProfitMargin.toFixed(1)}%` : "\u2014"}
        unavailableReason={avgProfitMargin == null ? (avgProfitMarginUnavailable ?? undefined) : undefined}
        testId="kpi-avg-profit-margin-value"
      />
      <KpiCell
        label="SCORE DELTA"
        value={scoreDelta != null ? `${scoreDelta > 0 ? "+" : ""}${scoreDelta.toFixed(1)}` : "\u2014"}
        color={scoreDelta != null ? (scoreDelta >= 0 ? "text-emerald-400" : "text-red-400") : undefined}
        unavailableReason={scoreDelta == null ? "First scoring run" : undefined}
        testId="kpi-score-delta-value"
      />
      <div className="col-span-2">
        <KpiCell
          label="PRICE DELTA"
          value={delta != null ? `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(1)}%` : "\u2014"}
          color={delta != null ? (delta >= 0 ? "text-emerald-400" : "text-red-400") : undefined}
          unavailableReason={delta == null ? (deltaUnavailable ?? "Requires valuation data") : undefined}
          testId="kpi-price-delta-value"
        />
      </div>
    </div>
  )
}
