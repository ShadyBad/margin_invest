import Link from "next/link"
import type { ScoreResponse, ScoreHistoryResponse } from "@/lib/api/types"
import { HeroHeader } from "./hero-header"
import { EliminatedHero } from "./eliminated-hero"
import { EliminationGauntlet } from "./elimination-gauntlet"
import { ScoringPillars } from "./scoring-pillars"
import { ConvictionEngine } from "./conviction-engine"
import { ValuationSection } from "./valuation-section"
import { HypotheticalScores } from "./hypothetical-scores"

interface AssetDetailViewProps {
  ticker: string
  scoreData: ScoreResponse | null
  historyData: ScoreHistoryResponse | null
  apiError: string | null
}

export function AssetDetailView({ ticker, scoreData, historyData, apiError }: AssetDetailViewProps) {
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
        />
      )}

      <EliminationGauntlet
        filters={scoreData.filters_passed}
        eliminated={!allFiltersPassed}
      />

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
          /* institutionalAccumulation — wired when API provides institutional_accumulation */
        />
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
    </div>
  )
}
