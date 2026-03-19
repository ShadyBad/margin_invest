"use client"

import { useState, useEffect, useCallback } from "react"
import { SeedDistributionTable } from "@/components/admin/SeedDistributionTable"
import { SeedBoxPlot } from "@/components/admin/SeedBoxPlot"
import { SeedDetailTable } from "@/components/admin/SeedDetailTable"
import { ValidationChecklist } from "@/components/admin/ValidationChecklist"
import {
  getLatestValidationReport,
  type SeedValidationReport,
} from "@/lib/api/model-validation"

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

export default function ModelValidationPage() {
  const [report, setReport] = useState<SeedValidationReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getLatestValidationReport()
      setReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch validation report")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  return (
    <div data-testid="model-validation-page" className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-text-primary mb-1">
        Model Validation
      </h1>
      <p className="text-sm text-text-tertiary mb-6">
        Seed validation reports for ML model training runs
      </p>

      {/* Loading state */}
      {loading && (
        <div className="text-center py-12 text-text-tertiary text-sm">
          Loading validation report...
        </div>
      )}

      {/* Error state */}
      {error && (
        <div data-testid="error-state" className="terminal-card p-4 mb-4 text-bearish text-sm">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !report && (
        <div data-testid="empty-state" className="text-center py-12 text-text-tertiary text-sm">
          No validation reports found.
        </div>
      )}

      {/* Report content */}
      {!loading && report && (
        <div className="space-y-6">
          {/* Summary header */}
          <div data-testid="summary-header" className="terminal-card p-5">
            <div className="flex flex-wrap items-center gap-4 mb-3">
              <h2 className="text-lg font-semibold text-text-primary">
                Run Report
              </h2>
              <span
                data-testid="gate-badge"
                className={`px-2.5 py-0.5 text-xs font-mono font-semibold uppercase tracking-wider rounded-full ${
                  report.gate_passed
                    ? "bg-[var(--color-bullish)]/20 text-bullish"
                    : "bg-[var(--color-bearish)]/20 text-bearish"
                }`}
              >
                {report.gate_passed ? "PASSED" : "FAILED"}
              </span>
            </div>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <dt className="text-text-tertiary">Run Group</dt>
                <dd className="font-mono text-text-primary text-xs mt-0.5 break-all">
                  {report.run_group_id}
                </dd>
              </div>
              <div>
                <dt className="text-text-tertiary">Timestamp</dt>
                <dd className="font-mono text-text-primary text-xs mt-0.5">
                  {formatTimestamp(report.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-text-tertiary">Seeds Evaluated</dt>
                <dd className="font-mono text-text-primary mt-0.5">
                  {report.n_seeds}
                </dd>
              </div>
              <div>
                <dt className="text-text-tertiary">Selected Seed</dt>
                <dd className="font-mono text-text-primary mt-0.5">
                  {report.selected_seed !== null ? `Seed ${report.selected_seed}` : "None"}
                </dd>
              </div>
            </dl>
          </div>

          {/* Validation checklist */}
          <ValidationChecklist
            checks={report.gate_checks}
            gatePassed={report.gate_passed}
          />

          {/* Model comparison (if exists) */}
          {report.comparison && (
            <div data-testid="comparison-section" className="terminal-card p-5">
              <h3 className="text-sm font-semibold text-text-primary mb-3">
                Model Comparison
              </h3>
              <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="text-text-tertiary">Label</dt>
                  <dd className="text-text-primary mt-0.5">{report.comparison.label}</dd>
                </div>
                <div>
                  <dt className="text-text-tertiary">P-Value</dt>
                  <dd className="font-mono text-text-primary mt-0.5">
                    {report.comparison.p_value.toFixed(4)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-tertiary">Effect Size</dt>
                  <dd className="font-mono text-text-primary mt-0.5">
                    {report.comparison.effect_size.toFixed(4)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-tertiary">Mean Difference</dt>
                  <dd className="font-mono text-text-primary mt-0.5">
                    {report.comparison.mean_difference.toFixed(4)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-tertiary">Samples Compared</dt>
                  <dd className="font-mono text-text-primary mt-0.5">
                    {report.comparison.n_compared}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-tertiary">Significant</dt>
                  <dd
                    className={`font-mono mt-0.5 ${
                      report.comparison.significant ? "text-bullish" : "text-text-secondary"
                    }`}
                  >
                    {report.comparison.significant ? "Yes" : "No"}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {/* Seed distribution table */}
          <SeedDistributionTable distributions={report.metric_distributions} />

          {/* Seed box plot */}
          <SeedBoxPlot seedDetails={report.seed_details} threshold={0.15} />

          {/* Seed detail table */}
          <SeedDetailTable details={report.seed_details} />
        </div>
      )}
    </div>
  )
}
