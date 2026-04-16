"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import type {
  ScoreResponse,
  ScoreHistoryResponse,
  BacktestTeaserResponse,
} from "@/lib/api/types"
import { getBacktestTeaser } from "@/lib/api/backtest"
import { InstrumentHeader } from "./instrument-header"
import { VitalSigns } from "./vital-signs"
import { FactorProfile } from "./factor-profile"
import { EliminationGauntlet } from "./elimination-gauntlet"
import { ScoringPillars } from "./scoring-pillars"
import { ConvictionEngine } from "./conviction-engine"
import { ValuationSection } from "./valuation-section"
import { InstitutionalPositioning } from "./institutional-positioning"
import { ModelValidation } from "./model-validation"

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

export function AssetDetailView({
  ticker,
  scoreData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  historyData,
  apiError,
  totalScored,
  filtersSurvivedCount,
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
      <div className="space-y-6 max-w-6xl mx-auto">
        <div
          className="rounded-lg p-8 text-center space-y-3"
          style={{
            backgroundColor: "var(--color-surface-container-low)",
            border: "1px solid var(--color-ghost)",
          }}
          data-testid="error-state"
        >
          <div className="mb-2" aria-hidden="true">
            <svg
              className="w-10 h-10 mx-auto"
              style={{ color: "var(--color-on-surface-variant)" }}
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
          <h2
            className="text-lg font-semibold"
            style={{ color: "var(--color-on-surface)" }}
          >
            Score data unavailable
          </h2>
          <p
            className="text-sm max-w-md mx-auto"
            style={{ color: "var(--color-on-surface-variant)" }}
          >
            This ticker will be scored in the next cycle. Check back after
            market close.
          </p>
        </div>
      </div>
    )
  }

  // --- Derived data ---
  const allFiltersPassed = scoreData.filters_passed.every((f) => f.passed)
  const derivedTier = deriveCompositeTier(scoreData.score)
  const TOP_TIERS = ["exceptional", "high", "medium"]
  const isTopTier = TOP_TIERS.includes(derivedTier)
  const showScoreView = allFiltersPassed || isTopTier

  // Build 5-factor percentiles for the FactorProfile.
  const sentimentSubScore = scoreData.momentum?.sub_scores?.find(
    (s) => s.name === "sentiment"
  )
  const factorPercentiles = {
    quality: scoreData.quality.average_percentile,
    value: scoreData.value.average_percentile,
    momentum: scoreData.momentum.average_percentile,
    sentiment: sentimentSubScore?.percentile_rank ?? null,
    growth: scoreData.growth?.average_percentile ?? null,
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Instrument Header -- full-width verdict */}
      <InstrumentHeader
        ticker={scoreData.ticker}
        name={scoreData.name}
        sector={scoreData.sector ?? null}
        growthStage={scoreData.growth_stage ?? null}
        style={scoreData.style ?? null}
        score={scoreData.score}
        tier={derivedTier}
        signal={scoreData.signal ?? null}
        scoredAt={scoreData.scored_at ?? null}
        eliminated={!showScoreView}
        eliminationReason={!showScoreView ? scoreData.filters_passed.find(f => !f.passed)?.name : null}
        universePercentile={scoreData.universe_percentile}
      />

      {/* Vital Signs -- full-width metrics */}
      <VitalSigns
        currentPrice={scoreData.actual_price}
        targetPrice={scoreData.buy_price}
        marginOfSafety={scoreData.margin_of_safety}
        compositePercentile={scoreData.universe_percentile}
        filtersPassed={scoreData.filters_passed.filter(f => f.passed).length}
        filtersTotal={scoreData.filters_passed.length}
        eliminated={!showScoreView}
        consistencyWarnings={scoreData.consistency_warnings?.map(w => w.field_name)}
      />

      {/* Factor Profile + Elimination Gauntlet -- 2-column */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FactorProfile
          factors={factorPercentiles}
          eliminated={!showScoreView}
        />
        <EliminationGauntlet
          filters={scoreData.filters_passed}
          eliminated={!showScoreView}
          totalScored={totalScored}
          filtersSurvivedCount={filtersSurvivedCount}
          sectorName={scoreData.sector ?? undefined}
        />
      </div>

      {/* Scoring Pillars -- full-width 3-column (only if passed) */}
      {showScoreView && (
        <ScoringPillars
          quality={scoreData.quality}
          value={scoreData.value}
          momentum={scoreData.momentum}
          growthStage={scoreData.growth_stage}
        />
      )}

      {/* Conviction Engine -- full-width (only if passed) */}
      {showScoreView && (
        <ConvictionEngine
          opportunityType={scoreData.opportunity_type ?? null}
          asymmetryRatio={scoreData.asymmetry_ratio ?? null}
          maxPositionPct={scoreData.max_position_pct ?? null}
          timingSignal={scoreData.timing_signal ?? null}
        />
      )}

      {/* Valuation Evidence -- full-width (only if passed) */}
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
          invalidReason={scoreData.price_target_invalid_reason ?? null}
        />
      )}

      {/* Institutional + Model Validation -- 2-column (only if passed) */}
      {showScoreView && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InstitutionalPositioning ticker={ticker} />
          <ModelValidation
            mlModelQualified={scoreData.ml_model_qualified ?? null}
            mlModelRankIc={scoreData.ml_model_rank_ic ?? null}
            mlModelTrainedAt={scoreData.ml_model_trained_at ?? null}
            mlAlpha={scoreData.ml_alpha ?? null}
            mlConfidence={scoreData.ml_confidence ?? null}
            mlOverride={scoreData.ml_override ?? null}
            rulesTier={scoreData.rules_conviction ?? null}
            compositeTier={scoreData.composite_tier ?? null}
            backtestData={teaserData}
          />
        </div>
      )}

      {/* Eliminated: explore link */}
      {!showScoreView && (
        <div className="text-center py-8">
          <Link
            href="/explore"
            className="text-sm transition-colors duration-150"
            style={{ color: "var(--color-primary-muted)" }}
          >
            View another candidate &rarr;
          </Link>
        </div>
      )}
    </div>
  )
}
