"use client"

import { useEffect, useState } from "react"
import { formatScoredAt } from "@/lib/format"
import { AppShell } from "@/components/layout"
import {
  AuditLog,
  CapacityChart,
  CostDisclosure,
  CostSensitivity,
  EquityCurve,
  FactorTimeline,
  FailureAudit,
  KnobsPanel,
  MetricsSummary,
  PerformanceChart,
  RegimeCards,
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
  getDefaultBacktest,
  getShadowPortfolio,
} from "@/lib/api/backtest"
import type {
  BacktestResult,
  BacktestMetrics,
  BacktestSummary,
  FullBacktestResponse,
  ShadowPortfolioResponse,
  RegimeSegmentResponse,
  AuditRecordResponse,
  FactorTimelineResponse,
  FailurePeriodResponse,
} from "@/lib/api/types"

// ---------------------------------------------------------------------------
// Transform functions: API response shapes → component prop shapes
// ---------------------------------------------------------------------------

const REGIME_LABELS: Record<string, string> = {
  bull: "Bull Market",
  bear: "Bear Market",
  sideways: "Sideways",
  crisis: "Crisis",
}

function toRegimePerformance(segments: RegimeSegmentResponse[]): RegimePerformance[] {
  return segments.map((s) => ({
    regime: s.regime as "bull" | "bear" | "sideways" | "crisis",
    label: REGIME_LABELS[s.regime] ?? s.regime,
    modelReturn: s.num_months > 0 ? (s.total_return / s.num_months) * 12 : 0,
    benchmarkReturn: s.num_months > 0 ? (s.benchmark_return / s.num_months) * 12 : 0,
    months: s.num_months,
    excessReturn: s.num_months > 0 ? ((s.total_return - s.benchmark_return) / s.num_months) * 12 : 0,
  }))
}

function toEquityCurvePoints(
  curve: { date: string; portfolio_value: number; benchmark_value: number }[],
): EquityCurvePoint[] {
  let peak = 0
  return curve.map((p) => {
    peak = Math.max(peak, p.portfolio_value)
    const drawdown = peak > 0 ? (p.portfolio_value - peak) / peak : 0
    return {
      date: p.date,
      portfolioValue: p.portfolio_value,
      benchmarkValue: p.benchmark_value,
      drawdown,
    }
  })
}

function toRegimeBands(
  segments: RegimeSegmentResponse[],
  curveLength: number,
): RegimeBand[] {
  if (curveLength === 0 || segments.length === 0) return []
  const bands: RegimeBand[] = []
  let idx = 0
  for (const s of segments) {
    const end = Math.min(idx + s.num_months, curveLength)
    if (idx < curveLength) {
      bands.push({
        startIndex: idx,
        endIndex: end,
        regime: s.regime as "bull" | "bear" | "sideways" | "crisis",
      })
    }
    idx = end
  }
  return bands
}

function toFactorEntries(timeline: FactorTimelineResponse[]): FactorAvailabilityEntry[] {
  return timeline.map((t) => ({ date: t.as_of_date, factors: t.available }))
}

function toAuditEntries(log: AuditRecordResponse[]) {
  return log.map((a) => ({
    date: a.rebalance_date,
    action: "rebalance",
    universeSize: a.universe_size,
    selectedCount: a.selected_count,
    factorCoverage: a.factor_coverage,
    regime: a.regime,
    turnover: 0,
  }))
}

function toStats(m: BacktestMetrics) {
  return {
    cagr: m.cagr,
    excessCagr: m.excess_cagr,
    sharpe: m.sharpe_ratio,
    sortino: m.sortino_ratio,
    maxDrawdown: m.max_drawdown,
    winRate: m.win_rate,
    informationRatio: m.information_ratio,
    totalReturn: m.total_return,
    benchmarkReturn: m.benchmark_total_return,
    numMonths: m.num_months,
    avgTurnover: m.avg_turnover,
  }
}

function toFailurePeriods(failures: FailurePeriodResponse[]) {
  return failures.map((f) => ({
    startDate: f.rebalance_date,
    endDate: f.rebalance_date,
    returnPct: f.portfolio_return,
    benchmarkReturnPct: f.benchmark_return,
    regime: f.regime,
    maxDrawdown: Math.abs(f.portfolio_return),
    recoveryMonths: null as number | null,
  }))
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function BacktestingPage() {
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [history, setHistory] = useState<BacktestSummary[]>([])
  const [replayData, setReplayData] = useState<FullBacktestResponse | null>(null)
  const [shadowData, setShadowData] = useState<ShadowPortfolioResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Knobs state — seeded from API config when available
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

        // Fetch replay and shadow portfolio data
        const [replay, shadow] = await Promise.all([
          getDefaultBacktest().catch(() => null),
          getShadowPortfolio().catch(() => null),
        ])
        if (cancelled) return
        setReplayData(replay)
        setShadowData(shadow)

        // Seed knobs from API config
        if (replay?.config) {
          setRebalanceFrequency(replay.config.rebalance_frequency)
          setTransactionCostBps(replay.config.transaction_cost_bps)
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

  // Derive component data from API response
  const metrics = replayData?.metrics ?? result?.metrics ?? null
  const regimes = replayData ? toRegimePerformance(replayData.regime_segments) : []
  const equityPoints = replayData ? toEquityCurvePoints(replayData.equity_curve) : []
  const regimeBands = replayData ? toRegimeBands(replayData.regime_segments, equityPoints.length) : []
  const factorEntries = replayData ? toFactorEntries(replayData.factor_timeline) : []
  const auditEntries = replayData ? toAuditEntries(replayData.audit_log) : []
  const failurePeriods = replayData ? toFailurePeriods(replayData.failure_audit) : []
  const stats = metrics ? toStats(metrics) : null

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
              <RegimeCards regimes={regimes} />
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
                    points={equityPoints}
                    regimeBands={regimeBands}
                  />
                </section>

                {/* Factor Availability Timeline */}
                <section>
                  <FactorTimeline entries={factorEntries} />
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
                {stats && <StatsSummary stats={stats} />}
              </div>
            </div>

            {/* -------------------------------------------------------------- */}
            {/* Section 3 — Existing metrics from API                         */}
            {/* -------------------------------------------------------------- */}
            {metrics && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Latest Performance Metrics
                </h2>
                <MetricsSummary metrics={metrics} />
              </section>
            )}

            {/* -------------------------------------------------------------- */}
            {/* Section 3b — Cost Sensitivity Analysis                         */}
            {/* -------------------------------------------------------------- */}
            {replayData?.sensitivity && replayData.sensitivity.rows.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Cost Sensitivity Analysis
                </h2>
                <CostSensitivity rows={replayData.sensitivity.rows} />
              </section>
            )}

            {/* -------------------------------------------------------------- */}
            {/* Section 3c — Capacity Analysis                                 */}
            {/* -------------------------------------------------------------- */}
            {replayData?.capacity && replayData.capacity.rows.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Capacity Analysis
                </h2>
                <CapacityChart
                  rows={replayData.capacity.rows}
                  breakevenAum={replayData.capacity.breakeven_aum}
                />
              </section>
            )}

            {/* -------------------------------------------------------------- */}
            {/* Section 3d — Cost Disclosure                                    */}
            {/* -------------------------------------------------------------- */}
            <section>
              <CostDisclosure costValidation={replayData?.cost_validation} />
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
            {auditEntries.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Rebalance Audit Log
                </h2>
                <AuditLog entries={auditEntries} />
              </section>
            )}

            {failurePeriods.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Worst Periods
                </h2>
                <FailureAudit periods={failurePeriods} />
              </section>
            )}

            {/* -------------------------------------------------------------- */}
            {/* Honesty Footer                                                 */}
            {/* -------------------------------------------------------------- */}
            <div
              className="terminal-card p-4 text-center"
              data-testid="backtest-disclosure"
            >
              <p className="text-xs text-text-tertiary">
                {replayData?.honesty_disclosure ??
                  "Backtest results are simulated and do not guarantee future performance. Past performance is not indicative of future results."}
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

        {!loading && !error && shadowData && (
          <section className="mt-8" data-testid="shadow-portfolio-section">
            <h2 className="text-lg font-semibold text-text-primary mb-4">
              Shadow Portfolio
            </h2>
            <div className="bg-bg-elevated border border-border-primary rounded-sm p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-text-secondary">Start Date</p>
                  <p className="text-sm font-mono text-text-primary">{shadowData.start_date}</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Total Return</p>
                  <p className="text-sm font-mono text-text-primary">{(shadowData.total_return * 100).toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Max Drawdown</p>
                  <p className="text-sm font-mono text-text-primary">{(shadowData.max_drawdown * 100).toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-xs text-text-secondary">Days Tracked</p>
                  <p className="text-sm font-mono text-text-primary">{shadowData.num_days}</p>
                </div>
              </div>
              {shadowData.cannot_be_backdated && (
                <p className="text-xs text-text-secondary mt-3" data-testid="shadow-no-backdate">
                  Shadow portfolio tracks forward only and cannot be backdated.
                </p>
              )}
            </div>
          </section>
        )}


      </div>
    </AppShell>
  )
}
