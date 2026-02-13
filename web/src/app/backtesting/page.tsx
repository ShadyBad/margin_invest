"use client"

import { useEffect, useState, useCallback } from "react"
import { AppShell } from "@/components/layout"
import { MetricsSummary, ValidationBadges } from "@/components/backtesting"
import { SkeletonCard, EmptyState } from "@/components/ui"
import {
  runBacktest,
  getBacktestResults,
  getBacktestResult,
} from "@/lib/api/backtest"
import type { BacktestResult } from "@/lib/api/types"

export default function BacktestingPage() {
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  const fetchLatest = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const listResponse = await getBacktestResults()
      if (listResponse.results.length > 0) {
        const latest = await getBacktestResult(listResponse.results[0].id)
        setResult(latest)
      } else {
        setResult(null)
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load backtest results",
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError(null)
        const listResponse = await getBacktestResults()
        if (cancelled) return
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
            : "Failed to load backtest results",
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

  async function handleRunBacktest() {
    try {
      setRunning(true)
      setError(null)
      await runBacktest()
      await fetchLatest()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to run backtest",
      )
    } finally {
      setRunning(false)
    }
  }

  return (
    <AppShell>
      <div data-testid="backtesting-page">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">
              Backtesting
            </h1>
            {result && (
              <p className="text-sm text-text-secondary mt-1">
                Last run:{" "}
                {new Date(result.run_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
                {" "}({result.duration_seconds.toFixed(1)}s)
              </p>
            )}
          </div>
          <button
            onClick={handleRunBacktest}
            disabled={running}
            className="px-4 py-2 bg-gold text-bg-primary font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            data-testid="run-backtest-button"
          >
            {running ? "Running..." : "Run Backtest"}
          </button>
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
            className="bg-bearish/10 border border-bearish/30 rounded-xl p-4 text-bearish"
            data-testid="error-message"
          >
            {error}
          </div>
        )}

        {!loading && !error && !result && (
          <EmptyState
            title="No backtests yet"
            description="Run your first backtest to see performance metrics and validation results."
          />
        )}

        {!loading && !error && result && (
          <div className="space-y-8">
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Performance Metrics
              </h2>
              <MetricsSummary metrics={result.metrics} />
            </section>

            {result.validation && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Validation
                </h2>
                <ValidationBadges validation={result.validation} />
              </section>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}
