"use client"

import { ProGate } from "./pro-gate"
import type { InstitutionalMetrics as Metrics } from "@/lib/compute-institutional-metrics"

interface MetricCellProps {
  label: string
  value: string
  context?: string
}

function MetricCell({ label, value, context }: MetricCellProps) {
  return (
    <div className="bg-bg-subtle/50 border border-border-primary/30 rounded-sm p-5 transition-all duration-200 hover:bg-bg-subtle/80 hover:shadow-sm">
      <div className="text-xs font-medium tracking-widest uppercase text-text-tertiary">
        {label}
      </div>
      <div className="text-2xl font-mono font-bold text-text-primary mt-2">
        {value}
      </div>
      {context && (
        <div className="text-xs text-text-secondary mt-3">{context}</div>
      )}
    </div>
  )
}

interface InstitutionalMetricsProps {
  metrics: Metrics | null
  className?: string
}

export function InstitutionalMetrics({ metrics, className = "" }: InstitutionalMetricsProps) {
  if (!metrics) return null

  return (
    <ProGate className={className}>
      <div
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
        data-testid="institutional-metrics"
      >
        <MetricCell
          label="SHARPE RATIO"
          value={metrics.sharpeRatio != null ? metrics.sharpeRatio.toFixed(2) : "N/A"}
        />
        <MetricCell
          label="MAX DRAWDOWN"
          value={`${(metrics.maxDrawdown * 100).toFixed(1)}%`}
        />
        <MetricCell
          label="VOLATILITY"
          value={metrics.volatility != null ? `${metrics.volatility.toFixed(1)}%` : "N/A"}
        />
        <MetricCell
          label="AVG PROFIT MARGIN"
          value={metrics.avgProfitMargin != null ? `${metrics.avgProfitMargin.toFixed(1)}%` : "N/A"}
        />
        <MetricCell
          label="RISK CLASSIFICATION"
          value={metrics.riskClassification}
        />
        <MetricCell
          label="ALLOCATION WEIGHT"
          value={metrics.allocationWeight != null ? `${metrics.allocationWeight.toFixed(1)}%` : "N/A"}
          context="of portfolio"
        />
      </div>
    </ProGate>
  )
}
