"use client"

import type { SeedDetail } from "@/lib/api/model-validation"

interface SeedDetailTableProps {
  details: SeedDetail[]
}

export function SeedDetailTable({ details }: SeedDetailTableProps) {
  const sorted = details.slice().sort((a, b) => a.seed - b.seed)

  if (sorted.length === 0) {
    return (
      <div data-testid="seed-detail-table" className="terminal-card p-5">
        <p className="text-sm text-text-tertiary">No seed details available.</p>
      </div>
    )
  }

  return (
    <div data-testid="seed-detail-table" className="terminal-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        Per-Seed Results
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary text-left text-text-secondary">
              <th className="pb-2 pr-4 font-medium">Seed</th>
              <th className="pb-2 pr-4 font-medium text-right">Rank IC</th>
              <th className="pb-2 pr-4 font-medium text-right">Clusters</th>
              <th className="pb-2 pr-4 font-medium text-right">Samples</th>
              <th className="pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((detail) => (
              <tr
                key={detail.seed}
                className={`border-b border-border-primary/50 ${
                  detail.selected ? "bg-accent/10" : ""
                }`}
                data-testid={`seed-row-${detail.seed}`}
              >
                <td className="py-2 pr-4 font-mono text-text-primary">
                  Seed {detail.seed}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {detail.rank_ic.toFixed(4)}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {detail.n_clusters}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-text-secondary">
                  {detail.n_samples}
                </td>
                <td className="py-2">
                  {detail.selected ? (
                    <span
                      className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-accent/20 text-accent"
                      data-testid={`selected-badge-${detail.seed}`}
                    >
                      Selected
                    </span>
                  ) : (
                    <span className="text-xs text-text-tertiary">&mdash;</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
