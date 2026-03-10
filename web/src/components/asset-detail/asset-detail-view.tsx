"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import type {
  ScoreResponse,
  ScoreHistoryResponse,
  BacktestTeaserResponse,
} from "@/lib/api/types"
import { getBacktestTeaser } from "@/lib/api/backtest"
import { formatScoredAt } from "@/lib/format"
import { HeroHeader } from "./hero-header"
import { EliminatedHero } from "./eliminated-hero"
import { EliminationGauntlet } from "./elimination-gauntlet"
import { ScoringPillars } from "./scoring-pillars"
import { ConvictionEngine } from "./conviction-engine"
import { ValuationSection } from "./valuation-section"
import { HypotheticalScores } from "./hypothetical-scores"
import { MLAuditPanel } from "./ml-audit-panel"
import { InstitutionalPositioning } from "./institutional-positioning"
import { BacktestTeaser } from "./backtest-teaser"
import { ConsistencyBadge } from "./consistency-badge"
import { DeterminismBadge } from "./determinism-badge"
import { FactorRadar } from "./factor-radar"
import { SectorNeutralBanner } from "./sector-neutral-banner"
import {
  FailedComparison,
  type FailedFilterComparison,
} from "./failed-comparison"
import { ScoreHeader } from "./score-header"
import { PriceContext } from "./price-context"
import { FactorPanel } from "./factor-panel"
import { FILTER_METADATA } from "@/lib/filter-metadata"

interface AssetDetailViewProps {
  ticker: string
  scoreData: ScoreResponse | null
  historyData: ScoreHistoryResponse | null
  apiError: string | null
  totalScored?: number
  filtersSurvivedCount?: number
  sectorSurvivorCount?: number
  sectorName?: string
}

/** Re-derive composite tier from raw score — mirrors the dashboard endpoint's
 *  _derive_composite_tier() thresholds so the detail page matches the picks list. */
function deriveCompositeTier(rawScore: number | null | undefined): string {
  if (rawScore == null) return "none"
  if (rawScore >= 76.0) return "exceptional"
  if (rawScore >= 71.0) return "high"
  if (rawScore >= 66.0) return "medium"
  return "none"
}

function formatGrowthStage(stage: string): string {
  return stage
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ")
}

function getFreshnessLabel(scoredAt: string | null | undefined): string {
  if (!scoredAt) return "N/A"
  return formatScoredAt(scoredAt)
}

export function AssetDetailView({
  ticker,
  scoreData,
  historyData,
  apiError,
  totalScored,
  filtersSurvivedCount,
  sectorSurvivorCount,
  sectorName,
}: AssetDetailViewProps) {
  const [teaserData, setTeaserData] = useState<BacktestTeaserResponse | null>(
    null
  )

  useEffect(() => {
    getBacktestTeaser(ticker)
      .then(setTeaserData)
      .catch(() => {})
  }, [ticker])

  // --- Error / unavailable state ---
  if (apiError || !scoreData) {
    return (
      <div className="space-y-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-text-tertiary">
          <Link href="/" className="text-accent hover:text-accent-hover">
            Dashboard
          </Link>
          <span>/</span>
          <span className="text-text-secondary">{ticker}</span>
        </nav>

        <div className="terminal-card p-8 text-center space-y-3" data-testid="error-state">
          <div className="text-3xl text-text-tertiary mb-2" aria-hidden="true">
            {/* Chart icon */}
            <svg
              className="w-10 h-10 mx-auto text-text-tertiary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-text-primary">
            Score data unavailable
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto">
            This ticker will be scored in the next cycle. Check back after
            market close.
          </p>
        </div>
      </div>
    )
  }

  // --- Derived data ---
  const allFiltersPassed = scoreData.filters_passed.every((f) => f.passed)
  const failedCount = scoreData.filters_passed.filter((f) => !f.passed).length
  // The score endpoint may return composite_tier "none" for stocks that failed
  // filters, even when the score is high enough for a real tier. Re-derive the
  // tier from the raw score to match the dashboard endpoint's logic.
  const derivedTier = deriveCompositeTier(scoreData.score)
  const TOP_TIERS = ["exceptional", "high", "medium"]
  const isTopTier = TOP_TIERS.includes(derivedTier)
  const showScoreView = allFiltersPassed || isTopTier
  const scoreHistoryValues = historyData?.points
    ?.map((p) => p.composite_raw_score)
    .filter((v): v is number => v != null)
    .reverse()

  const failedFilterComparisons: FailedFilterComparison[] =
    scoreData.filters_passed
      .filter((f) => !f.passed)
      .map((f) => ({
        filterName: f.name,
        filterDisplayName: FILTER_METADATA[f.name]?.displayName || f.name,
        stockValue: f.value ?? 0,
        threshold: f.threshold ?? 0,
        championValue: null,
        championTicker: null,
        sectorMedian: null,
      }))

  // Build 5-factor percentiles for the FactorPanel
  const factorPercentiles = {
    quality: scoreData.quality.average_percentile,
    value: scoreData.value.average_percentile,
    momentum: scoreData.momentum.average_percentile,
    sentiment: scoreData.capital_allocation?.average_percentile ?? 50,
    growth: scoreData.catalyst?.average_percentile ?? 50,
  }

  const hasPriceData =
    scoreData.actual_price != null && scoreData.buy_price != null

  return (
    <div className="space-y-6">
      {/* --- Top context bar (above the grid) --- */}
      <nav
        className="flex items-center gap-2 text-sm text-text-tertiary"
        data-testid="breadcrumb"
      >
        <Link href="/" className="text-accent hover:text-accent-hover">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-text-secondary">{ticker}</span>
      </nav>

      {/* Ticker header + metadata */}
      <div className="space-y-2">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-title-1 text-text-primary">{scoreData.ticker}</h1>
          <span className="text-lg text-text-secondary">{scoreData.name}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-tertiary flex-wrap">
          {scoreData.sector && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08] font-mono">
              {scoreData.sector}
            </span>
          )}
          {scoreData.growth_stage && (
            <span>{formatGrowthStage(scoreData.growth_stage)}</span>
          )}
          {scoreData.style && (
            <>
              <span className="text-white/20">|</span>
              <span>
                {scoreData.style.charAt(0).toUpperCase() +
                  scoreData.style.slice(1)}
              </span>
            </>
          )}
          <span className="text-white/20">|</span>
          <span>Scored: {getFreshnessLabel(scoreData.scored_at)}</span>
        </div>
      </div>

      {/* --- Two-column grid --- */}
      <div className="grid grid-cols-1 lg:grid-cols-[60%_40%] gap-6" data-testid="detail-grid">
        {/* ---- Left column (60%) ---- */}
        <div className="space-y-6 min-w-0">
          {/* Score header (passed or top-tier) or eliminated hero */}
          {showScoreView ? (
            <>
              <ScoreHeader
                score={scoreData.score}
                tier={derivedTier}
                percentile={scoreData.universe_percentile}
              />

              {hasPriceData && (
                <PriceContext
                  actualPrice={scoreData.actual_price!}
                  buyPrice={scoreData.buy_price!}
                  marginOfSafety={scoreData.margin_of_safety ?? 0}
                />
              )}

              {/* Legacy hero header preserved below the new panels for full context */}
              <HeroHeader
                ticker={scoreData.ticker}
                name={scoreData.name}
                sector={scoreData.sector ?? undefined}
                growthStage={scoreData.growth_stage}
                actualPrice={scoreData.actual_price}
                compositeScore={scoreData.score}
                universePercentile={scoreData.universe_percentile}
                compositeTier={scoreData.composite_tier}
                signal={scoreData.signal}
                dataCoverage={scoreData.data_coverage}
                scoredAt={scoreData.scored_at}
                scoreHistory={scoreHistoryValues}
                style={scoreData.style}
              />
            </>
          ) : (
            <EliminatedHero
              ticker={scoreData.ticker}
              name={scoreData.name}
              growthStage={scoreData.growth_stage}
              actualPrice={scoreData.actual_price}
              failedCount={failedCount}
              totalFilters={scoreData.filters_passed.length}
              dataCoverage={scoreData.data_coverage}
              scoredAt={scoreData.scored_at}
              hypotheticalPercentile={scoreData.composite_percentile}
            />
          )}

          <DeterminismBadge />

          {scoreData.consistency_warnings &&
            scoreData.consistency_warnings.length > 0 && (
              <ConsistencyBadge warnings={scoreData.consistency_warnings} />
            )}

          <EliminationGauntlet
            filters={scoreData.filters_passed}
            eliminated={!showScoreView}
            totalScored={totalScored}
            filtersSurvivedCount={filtersSurvivedCount}
          />

          {!allFiltersPassed && !isTopTier && failedFilterComparisons.length > 0 && (
            <FailedComparison
              ticker={ticker}
              failedFilters={failedFilterComparisons}
            />
          )}

          {showScoreView && (
            <SectorNeutralBanner
              sectorName={scoreData.sector || "Unknown"}
            />
          )}

          {showScoreView && (
            <ScoringPillars
              quality={scoreData.quality}
              value={scoreData.value}
              momentum={scoreData.momentum}
              growthStage={scoreData.growth_stage}
            />
          )}

          {showScoreView && (
            <ConvictionEngine
              opportunityType={scoreData.opportunity_type ?? null}
              winningTrack={scoreData.winning_track ?? null}
              asymmetryRatio={scoreData.asymmetry_ratio ?? null}
              maxPositionPct={scoreData.max_position_pct ?? null}
              timingSignal={scoreData.timing_signal ?? null}
              capitalAllocation={scoreData.capital_allocation ?? null}
              catalyst={scoreData.catalyst ?? null}
              mlOverride={scoreData.ml_override ?? null}
              institutionalAccumulation={
                scoreData.institutional_accumulation
                  ? {
                      percentile:
                        scoreData.institutional_accumulation.percentile,
                      newPositions:
                        scoreData.institutional_accumulation.new_positions,
                      topFunds:
                        scoreData.institutional_accumulation.top_funds,
                    }
                  : undefined
              }
            />
          )}

          {showScoreView && (
            <MLAuditPanel
              mlModelQualified={scoreData.ml_model_qualified ?? null}
              mlModelRankIc={scoreData.ml_model_rank_ic ?? null}
              mlModelTrainedAt={scoreData.ml_model_trained_at ?? null}
              mlAlpha={scoreData.ml_alpha ?? null}
              mlConfidence={scoreData.ml_confidence ?? null}
              mlOverride={scoreData.ml_override ?? null}
              rulesTier={scoreData.rules_conviction ?? null}
              compositeTier={scoreData.composite_tier ?? null}
            />
          )}

          {showScoreView && (
            <InstitutionalPositioning ticker={ticker} />
          )}

          {showScoreView && (
            <ValuationSection
              ticker={scoreData.ticker}
              buyPrice={scoreData.buy_price}
              sellPrice={scoreData.sell_price}
              intrinsicValue={scoreData.margin_invest_value}
              currentPrice={scoreData.actual_price}
              priceUpside={scoreData.price_upside ?? null}
              marginOfSafety={scoreData.margin_of_safety ?? null}
              valuationMethods={scoreData.valuation_methods ?? null}
              invalidReason={
                scoreData.price_target_invalid_reason ?? null
              }
            />
          )}

          {showScoreView && teaserData && (
            <BacktestTeaser
              modelReturn={teaserData.model_return}
              benchmarkReturn={teaserData.benchmark_return}
              maxDrawdown={teaserData.max_drawdown}
              benchmarkMaxDrawdown={teaserData.benchmark_max_drawdown}
              startDate={teaserData.start_date}
            />
          )}

          {!showScoreView && (
            <HypotheticalScores
              ticker={scoreData.ticker}
              compositeScore={scoreData.score}
              compositePercentile={scoreData.universe_percentile}
              compositeTier={scoreData.composite_tier}
              quality={scoreData.quality}
              value={scoreData.value}
              momentum={scoreData.momentum}
              growthStage={scoreData.growth_stage}
            />
          )}

          {!showScoreView &&
            sectorSurvivorCount != null &&
            sectorSurvivorCount > 0 &&
            sectorName && (
              <div className="terminal-card p-4 text-center">
                <p className="text-sm text-text-secondary">
                  {sectorSurvivorCount} stock
                  {sectorSurvivorCount !== 1 ? "s" : ""} in {sectorName}{" "}
                  survived the gauntlet.
                </p>
                <Link
                  href={`/dashboard?sector=${encodeURIComponent(sectorName)}`}
                  className="text-sm text-accent hover:text-accent-hover mt-2 inline-block"
                >
                  View survivors &rarr;
                </Link>
              </div>
            )}
        </div>

        {/* ---- Right column (40%) ---- */}
        <div className="space-y-6">
          {showScoreView && (
            <FactorPanel factors={factorPercentiles} />
          )}

          {showScoreView && (
            <FactorRadar
              quality={scoreData.quality}
              value={scoreData.value}
              momentum={scoreData.momentum}
              sectorName={scoreData.sector ?? undefined}
            />
          )}
        </div>
      </div>
    </div>
  )
}
