"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import type { ScoreResponse, ScoreHistoryResponse, BacktestTeaserResponse } from "@/lib/api/types"
import { getBacktestTeaser } from "@/lib/api/backtest"
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
import { DeterminismBadge } from "./determinism-badge"
import { FactorRadar } from "./factor-radar"
import { SectorNeutralBanner } from "./sector-neutral-banner"
import { FailedComparison, type FailedFilterComparison } from "./failed-comparison"
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

export function AssetDetailView({ ticker, scoreData, historyData, apiError, totalScored, filtersSurvivedCount, sectorSurvivorCount, sectorName }: AssetDetailViewProps) {
  const [teaserData, setTeaserData] = useState<BacktestTeaserResponse | null>(null)

  useEffect(() => {
    getBacktestTeaser(ticker).then(setTeaserData).catch(() => {})
  }, [ticker])

  if (apiError || !scoreData) {
    return (
      <div className="space-y-4">
        <Link href="/" className="text-sm text-accent hover:text-accent-hover">
          &larr; Back to Dashboard
        </Link>
        <div className="terminal-card p-6 text-center">
          <p className="text-text-secondary">
            {apiError ?? `No data available for ${ticker}.`}
          </p>
        </div>
      </div>
    )
  }

  const allFiltersPassed = scoreData.filters_passed.every((f) => f.passed)
  const failedCount = scoreData.filters_passed.filter((f) => !f.passed).length
  const scoreHistoryValues = historyData?.points
    ?.map((p) => p.composite_raw_score)
    .filter((v): v is number => v != null)
    .reverse()

  const failedFilterComparisons: FailedFilterComparison[] = scoreData.filters_passed
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

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-accent hover:text-accent-hover">
        &larr; Back to Dashboard
      </Link>

      {allFiltersPassed ? (
        <HeroHeader
          ticker={scoreData.ticker}
          name={scoreData.name}
          sector={
            scoreData.filters_passed.length > 0
              ? undefined
              : undefined
          }
          growthStage={scoreData.growth_stage}
          actualPrice={scoreData.actual_price}
          compositeScore={scoreData.score}
          universePercentile={scoreData.universe_percentile}
          convictionLevel={scoreData.conviction_level}
          signal={scoreData.signal}
          dataCoverage={scoreData.data_coverage}
          scoredAt={scoreData.scored_at}
          scoreHistory={scoreHistoryValues}
          style={scoreData.style}
        />
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

      <EliminationGauntlet
        filters={scoreData.filters_passed}
        eliminated={!allFiltersPassed}
        totalScored={totalScored}
        filtersSurvivedCount={filtersSurvivedCount}
      />

      {!allFiltersPassed && failedFilterComparisons.length > 0 && (
        <FailedComparison ticker={ticker} failedFilters={failedFilterComparisons} />
      )}

      {allFiltersPassed && (
        <FactorRadar
          quality={scoreData.quality}
          value={scoreData.value}
          momentum={scoreData.momentum}
          sectorName={scoreData.sector}
        />
      )}

      {allFiltersPassed && (
        <SectorNeutralBanner sectorName={scoreData.sector || "Unknown"} />
      )}

      {allFiltersPassed && (
        <ScoringPillars
          quality={scoreData.quality}
          value={scoreData.value}
          momentum={scoreData.momentum}
          growthStage={scoreData.growth_stage}
        />
      )}

      {allFiltersPassed && (
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
                  percentile: scoreData.institutional_accumulation.percentile,
                  newPositions: scoreData.institutional_accumulation.new_positions,
                  topFunds: scoreData.institutional_accumulation.top_funds,
                }
              : undefined
          }
        />
      )}

      {allFiltersPassed && (
        <MLAuditPanel
          mlModelQualified={scoreData.ml_model_qualified ?? null}
          mlModelRankIc={scoreData.ml_model_rank_ic ?? null}
          mlModelTrainedAt={scoreData.ml_model_trained_at ?? null}
          mlAlpha={scoreData.ml_alpha ?? null}
          mlConfidence={scoreData.ml_confidence ?? null}
          mlOverride={scoreData.ml_override ?? null}
          rulesConviction={scoreData.rules_conviction ?? null}
          conviction={scoreData.conviction_level ?? null}
        />
      )}

      {allFiltersPassed && (
        <InstitutionalPositioning ticker={ticker} />
      )}

      {allFiltersPassed && (
        <ValuationSection
          ticker={scoreData.ticker}
          buyPrice={scoreData.buy_price}
          sellPrice={scoreData.sell_price}
          intrinsicValue={scoreData.margin_invest_value}
          currentPrice={scoreData.actual_price}
          priceUpside={scoreData.price_upside ?? null}
          marginOfSafety={scoreData.margin_of_safety ?? null}
          valuationMethods={scoreData.valuation_methods ?? null}
          invalidReason={scoreData.price_target_invalid_reason ?? null}
        />
      )}

      {allFiltersPassed && teaserData && (
        <BacktestTeaser
          modelReturn={teaserData.model_return}
          benchmarkReturn={teaserData.benchmark_return}
          maxDrawdown={teaserData.max_drawdown}
          benchmarkMaxDrawdown={teaserData.benchmark_max_drawdown}
          startDate={teaserData.start_date}
        />
      )}

      {!allFiltersPassed && (
        <HypotheticalScores
          ticker={scoreData.ticker}
          compositeScore={scoreData.score}
          compositePercentile={scoreData.universe_percentile}
          convictionLevel={scoreData.conviction_level}
          quality={scoreData.quality}
          value={scoreData.value}
          momentum={scoreData.momentum}
          growthStage={scoreData.growth_stage}
        />
      )}

      {!allFiltersPassed && sectorSurvivorCount != null && sectorSurvivorCount > 0 && sectorName && (
        <div className="terminal-card p-4 text-center">
          <p className="text-sm text-text-secondary">
            {sectorSurvivorCount} stock{sectorSurvivorCount !== 1 ? "s" : ""} in {sectorName} survived the gauntlet.
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
  )
}
