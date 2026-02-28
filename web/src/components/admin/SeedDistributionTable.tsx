"use client"

import type { MetricDistribution } from "@/lib/api/model-validation"

interface SeedDistributionTableProps {
  distributions: Record<string, MetricDistribution>
}

function fmt(value: number, decimals = 4): string {
  return value.toFixed(decimals)
}

function formatMetricName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function SeedDistributionTable({ distributions }: SeedDistributionTableProps) {
  const metrics = Object.entries(distributions)

  if (metrics.length === 0) {
    return (
      <div data-testid="seed-distribution-table" className="terminal-card p-5">
        <p className="text-sm text-text-tertiary">No distribution data available.</p>
      </div>
    )
  }

  return (
    <div data-testid="seed-distribution-table" className="terminal-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        Metric Distributions
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary text-left text-text-secondary">
              <th className="pb-2 pr-4 font-medium">Metric</th>
              <th className="pb-2 pr-4 font-medium text-right">Mean</th>
              <th className="pb-2 pr-4 font-medium text-right">Median</th>
              <th className="pb-2 pr-4 font-medium text-right">Std</th>
              <th className="pb-2 pr-4 font-medium text-right">Min</th>
              <th className="pb-2 pr-4 font-medium text-right">Max</th>
              <th className="pb-2 pr-4 font-medium text-right">95% CI</th>
              <th className="pb-2 font-medium text-right">CV</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map(([name, dist]) => (
              <tr
                key={name}
                className="border-b border-border-primary/50"
                data-testid={`dist-row-${name}`}
              >
                <td className="py-2 pr-4 text-text-primary">
                  {formatMetricName(name)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {fmt(dist.mean)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {fmt(dist.median)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {fmt(dist.std)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {fmt(dist.min)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {fmt(dist.max)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  [{fmt(dist.ci_lower, 3)}, {fmt(dist.ci_upper, 3)}]
                </td>
                <td className="py-2 text-right font-mono text-text-secondary">
                  {fmt(dist.cv, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
