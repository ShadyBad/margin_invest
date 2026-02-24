"use client"

import { useEffect, useState } from "react"
import { formatScoredAt } from "@/lib/format"
import { AppShell } from "@/components/layout"
import {
  AuditLog,
  EquityCurve,
  FactorTimeline,
  FailureAudit,
  KnobsPanel,
  MetricsSummary,
  PerformanceChart,
  RegimeCards,
  ShadowSection,
  StatsSummary,
  ValidationBadges,
} from "@/components/backtesting"
import type { RegimePerformance } from "@/components/backtesting"
import type { EquityCurvePoint, RegimeBand } from "@/components/backtesting"
import type { FactorAvailabilityEntry } from "@/components/backtesting"
import { SkeletonCard, EmptyState } from "@/components/ui"
import {
  getBacktestResults,
  getBacktestResult,
} from "@/lib/api/backtest"
import type { BacktestResult, BacktestSummary } from "@/lib/api/types"

// ---------------------------------------------------------------------------
// Mock data for new components (will be replaced with live API data)
// ---------------------------------------------------------------------------

const MOCK_REGIMES: RegimePerformance[] = [
  { regime: "bull", label: "Bull Market", modelReturn: 0.22, benchmarkReturn: 0.18, months: 96, excessReturn: 0.04 },
  { regime: "bear", label: "Bear Market", modelReturn: -0.08, benchmarkReturn: -0.15, months: 24, excessReturn: 0.07 },
  { regime: "sideways", label: "Sideways", modelReturn: 0.06, benchmarkReturn: 0.04, months: 48, excessReturn: 0.02 },
  { regime: "crisis", label: "Crisis", modelReturn: -0.18, benchmarkReturn: -0.35, months: 12, excessReturn: 0.17 },
]

function generateEquityCurvePoints(): EquityCurvePoint[] {
  const points: EquityCurvePoint[] = []
  let portfolio = 1.0
  let benchmark = 1.0
  let peak = 1.0
  const startYear = 2005
  for (let m = 0; m < 240; m++) {
    const year = startYear + Math.floor(m / 12)
    const month = (m % 12) + 1
    const date = `${year}-${String(month).padStart(2, "0")}-28`
    // Simple deterministic growth with cycles
    const cycle = Math.sin(m / 24) * 0.02
    portfolio *= 1 + 0.008 + cycle + (m > 36 && m < 60 ? -0.025 : 0)
    benchmark *= 1 + 0.006 + cycle * 0.5 + (m > 36 && m < 60 ? -0.02 : 0)
    peak = Math.max(peak, portfolio)
    const drawdown = (portfolio - peak) / peak
    points.push({ date, portfolioValue: portfolio, benchmarkValue: benchmark, drawdown })
  }
  return points
}

const MOCK_EQUITY_POINTS: EquityCurvePoint[] = generateEquityCurvePoints()

const MOCK_REGIME_BANDS: RegimeBand[] = [
  { startIndex: 0, endIndex: 36, regime: "bull" },
  { startIndex: 36, endIndex: 60, regime: "bear" },
  { startIndex: 60, endIndex: 108, regime: "bull" },
  { startIndex: 108, endIndex: 120, regime: "crisis" },
  { startIndex: 120, endIndex: 168, regime: "sideways" },
  { startIndex: 168, endIndex: 240, regime: "bull" },
]

const MOCK_FACTOR_ENTRIES: FactorAvailabilityEntry[] = [
  { date: "2005-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth"] },
  { date: "2008-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth", "FCF Yield"] },
  { date: "2012-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth", "FCF Yield", "Debt/Equity"] },
  { date: "2015-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth", "FCF Yield", "Debt/Equity", "Insider Activity"] },
  { date: "2018-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth", "FCF Yield", "Debt/Equity", "Insider Activity", "Institutional Flow"] },
  { date: "2022-01-01", factors: ["PE", "PB", "ROE", "Revenue Growth", "FCF Yield", "Debt/Equity", "Insider Activity", "Institutional Flow"] },
]

const MOCK_AUDIT_ENTRIES = [
  { date: "2025-12-31", action: "rebalance", universeSize: 502, selectedCount: 5, factorCoverage: 0.95, regime: "bull", turnover: 0.40 },
  { date: "2025-11-30", action: "rebalance", universeSize: 500, selectedCount: 5, factorCoverage: 0.94, regime: "bull", turnover: 0.20 },
  { date: "2025-10-31", action: "rebalance", universeSize: 498, selectedCount: 5, factorCoverage: 0.93, regime: "sideways", turnover: 0.60 },
  { date: "2025-09-30", action: "rebalance", universeSize: 501, selectedCount: 5, factorCoverage: 0.95, regime: "sideways", turnover: 0.20 },
  { date: "2025-08-31", action: "rebalance", universeSize: 499, selectedCount: 5, factorCoverage: 0.92, regime: "bull", turnover: 0.40 },
]

const MOCK_STATS = {
  cagr: 0.1234,
  excessCagr: 0.0456,
  sharpe: 1.52,
  sortino: 2.13,
  maxDrawdown: 0.2145,
  winRate: 0.5832,
  informationRatio: 0.87,
  totalReturn: 0.7523,
  benchmarkReturn: 0.5012,
  numMonths: 240,
  avgTurnover: 0.15,
  calmarRatio: 0.575,
}

const MOCK_FAILURE_PERIODS = [
  { startDate: "2008-09-01", endDate: "2009-03-01", returnPct: -0.38, benchmarkReturnPct: -0.52, regime: "crisis", maxDrawdown: 0.42, recoveryMonths: 18 },
  { startDate: "2020-02-01", endDate: "2020-04-01", returnPct: -0.22, benchmarkReturnPct: -0.34, regime: "crisis", maxDrawdown: 0.25, recoveryMonths: 5 },
  { startDate: "2022-01-01", endDate: "2022-10-01", returnPct: -0.15, benchmarkReturnPct: -0.25, regime: "bear", maxDrawdown: 0.18, recoveryMonths: 8 },
]

const MOCK_SHADOW = {
  startDate: "2026-02-24",
  totalReturn: 0.0,
  maxDrawdown: 0.0,
  numDays: 1,
  positions: [] as { ticker: string; weight: number }[],
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function BacktestingPage() {
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [history, setHistory] = useState<BacktestSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Knobs state (mock — parameters are display-only for now)
  const [rebalanceFrequency, setRebalanceFrequency] = useState("monthly")
  const [topPercentile, setTopPercentile] = useState(10)
  const [transactionCostBps, setTransactionCostBps] = useState(10)
  const [slippageBps, setSlippageBps] = useState(5)

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
        {/* ---------------------------------------------------------------- */}
        {/* Header                                                           */}
        {/* ---------------------------------------------------------------- */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-text-primary font-[family-name:var(--font-display)]">
                Replay Backtesting
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
          <p className="text-sm text-text-secondary mt-2">
            Walk-forward simulation of the scoring model against historical data
          </p>
          <p
            className="text-xs text-text-tertiary mt-1"
            data-testid="auto-validation-note"
          >
            Backtesting runs automatically after each scoring cycle. Results
            are read-only.
          </p>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Loading / Error / Empty states                                   */}
        {/* ---------------------------------------------------------------- */}
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

        {/* ---------------------------------------------------------------- */}
        {/* Main content (when data loaded)                                  */}
        {/* ---------------------------------------------------------------- */}
        {!loading && !error && result && (
          <div className="space-y-8">
            {/* -------------------------------------------------------------- */}
            {/* Section 1 — Regime Performance Cards                           */}
            {/* -------------------------------------------------------------- */}
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Regime Performance
              </h2>
              <RegimeCards regimes={MOCK_REGIMES} />
            </section>

            {/* -------------------------------------------------------------- */}
            {/* Section 2 — Two-column layout: charts + sidebar               */}
            {/* -------------------------------------------------------------- */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
              <div className="space-y-6">
                {/* Equity Curve */}
                <section>
                  <h2 className="text-lg font-semibold text-text-primary mb-4">
                    Equity Curve
                  </h2>
                  <EquityCurve
                    points={MOCK_EQUITY_POINTS}
                    regimeBands={MOCK_REGIME_BANDS}
                  />
                </section>

                {/* Factor Availability Timeline */}
                <section>
                  <FactorTimeline entries={MOCK_FACTOR_ENTRIES} />
                </section>
              </div>

              <div className="space-y-6">
                {/* Knobs Panel */}
                <KnobsPanel
                  rebalanceFrequency={rebalanceFrequency}
                  topPercentile={topPercentile}
                  transactionCostBps={transactionCostBps}
                  slippageBps={slippageBps}
                  benchmarkTicker="SPY"
                  onRebalanceChange={setRebalanceFrequency}
                  onTopPercentileChange={setTopPercentile}
                  onTransactionCostChange={setTransactionCostBps}
                  onSlippageChange={setSlippageBps}
                  disabled={false}
                />

                {/* Stats Summary */}
                <StatsSummary stats={MOCK_STATS} />
              </div>
            </div>

            {/* -------------------------------------------------------------- */}
            {/* Section 3 — Existing metrics from API                         */}
            {/* -------------------------------------------------------------- */}
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Latest Performance Metrics
              </h2>
              <MetricsSummary metrics={result.metrics} />
            </section>

            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Historical Performance
              </h2>
              <PerformanceChart
                snapshots={result.snapshots ?? []}
                portfolioLabel="Up to 5, Exceptional then High, MoS > 20%, Equal-Weight, Monthly"
                benchmarkLabel="S&P 500 (SPY Total Return)"
                mosThreshold={0.20}
                maxHoldings={5}
              />
            </section>

            {result.validation && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Validation Checks
                </h2>
                <ValidationBadges validation={result.validation} />
              </section>
            )}

            {/* -------------------------------------------------------------- */}
            {/* Section 4 — Detail views                                      */}
            {/* -------------------------------------------------------------- */}
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Rebalance Audit Log
              </h2>
              <AuditLog entries={MOCK_AUDIT_ENTRIES} />
            </section>

            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Worst Periods
              </h2>
              <FailureAudit periods={MOCK_FAILURE_PERIODS} />
            </section>

            {/* -------------------------------------------------------------- */}
            {/* Section 5 — Shadow Portfolio                                   */}
            {/* -------------------------------------------------------------- */}
            <section>
              <ShadowSection
                startDate={MOCK_SHADOW.startDate}
                totalReturn={MOCK_SHADOW.totalReturn}
                maxDrawdown={MOCK_SHADOW.maxDrawdown}
                numDays={MOCK_SHADOW.numDays}
                positions={MOCK_SHADOW.positions}
              />
            </section>

            {/* -------------------------------------------------------------- */}
            {/* Honesty Footer                                                 */}
            {/* -------------------------------------------------------------- */}
            <div
              className="terminal-card p-4 text-center"
              data-testid="backtest-disclosure"
            >
              <p className="text-xs text-text-tertiary">
                Backtest results are simulated and do not guarantee future
                performance. Past performance is not indicative of future
                results.
              </p>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Validation History                                               */}
        {/* ---------------------------------------------------------------- */}
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
