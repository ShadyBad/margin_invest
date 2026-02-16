"use client"

import { useEffect, useState } from "react"
import { formatScoredAt } from "@/lib/format"
import { AppShell } from "@/components/layout"
import { MetricsSummary, ValidationBadges } from "@/components/backtesting"
import { SkeletonCard, EmptyState } from "@/components/ui"
import {
  getBacktestResults,
  getBacktestResult,
} from "@/lib/api/backtest"
import type { BacktestResult, BacktestSummary } from "@/lib/api/types"

export default function BacktestingPage() {
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [history, setHistory] = useState<BacktestSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError(null)
        const listResponse = await getBacktestResults()
        if (cancelled) return
        setHistory(listResponse.results)
        if (listResponse.results.length > 0) {
          const latest = await getBacktestResult(listResponse.results[0].id)
          if (cancelled) return
          setResult(latest)
        } else {
          setResult(null)
        }
      } catch (err) {
        if (cancelled) return
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load validation results",
        )
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <AppShell>
      <div data-testid="backtesting-page">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-text-primary">
                Methodology Validation
              </h1>
              {result && (
                <p className="text-sm text-text-secondary mt-1">
                  Last validated:{" "}
                  {formatScoredAt(result.run_at)}
                  {" "}({result.duration_seconds.toFixed(1)}s)
                </p>
              )}
            </div>
          </div>
          <p
            className="text-sm text-text-secondary mt-2"
            data-testid="auto-validation-note"
          >
            Backtesting runs automatically after each scoring cycle. Results
            are read-only.
          </p>
        </div>

        {loading && (
          <div
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
            data-testid="loading-skeleton"
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {error && (
          <div
            className="bg-bearish/10 border border-bearish/30 rounded-sm p-4 text-bearish"
            data-testid="error-message"
          >
            {error}
          </div>
        )}

        {!loading && !error && !result && (
          <EmptyState
            title="No validations yet"
            description="Validation results will appear here after the next scoring cycle completes."
          />
        )}

        {!loading && !error && result && (
          <div className="space-y-8">
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Latest Performance Metrics
              </h2>
              <MetricsSummary metrics={result.metrics} />
            </section>

            {result.validation && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Validation Checks
                </h2>
                <ValidationBadges validation={result.validation} />
              </section>
            )}
          </div>
        )}

        {!loading && !error && history.length > 0 && (
          <section className="mt-8" data-testid="validation-history">
            <h2 className="text-lg font-semibold text-text-primary mb-4">
              Validation History
            </h2>
            <div className="space-y-2">
              {history.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between bg-bg-elevated border border-border-primary rounded-sm px-4 py-3"
                  data-testid={`history-item-${entry.id}`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        entry.overall_pass === true
                          ? "bg-bullish"
                          : entry.overall_pass === false
                            ? "bg-bearish"
                            : "bg-text-secondary"
                      }`}
                    />
                    <span className="text-sm text-text-primary">
                      {formatScoredAt(entry.run_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-text-secondary">
                      Excess CAGR: {(entry.excess_cagr * 100).toFixed(2)}%
                    </span>
                    <span className="text-xs text-text-secondary">
                      Sharpe: {entry.sharpe_ratio.toFixed(2)}
                    </span>
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        entry.overall_pass === true
                          ? "bg-bullish/10 text-bullish"
                          : entry.overall_pass === false
                            ? "bg-bearish/10 text-bearish"
                            : "bg-bg-primary text-text-secondary"
                      }`}
                    >
                      {entry.overall_pass === true
                        ? "PASS"
                        : entry.overall_pass === false
                          ? "FAIL"
                          : "N/A"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppShell>
  )
}
