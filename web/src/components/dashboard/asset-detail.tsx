"use client"

import { useState } from "react"
import { ConvictionBadge } from "@/components/ui"
import { ActionPill } from "@/components/ui"
import { formatAttributeLabel, formatScoredAt } from "@/lib/format"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import { PriceChart } from "./price-chart"
import { ValuationBreakdown } from "./valuation-breakdown"
import { SignalTimeline } from "./signal-timeline"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetDetailProps {
  score: ScoreResponse
  className?: string
}


export function AssetDetail({ score, className = "" }: AssetDetailProps) {
  const [showData, setShowData] = useState(false)
  const hasV2 = score.opportunity_type != null

  return (
    <div
      className={`border-t border-border-primary pt-6 mt-4 ${className}`}
      data-testid={`asset-detail-${score.ticker}`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h3 className="text-xl font-bold text-text-primary">{score.ticker}</h3>
        <span className="text-sm text-text-secondary">{score.name}</span>
        <span className="text-lg font-bold text-accent ml-auto">
          {(score.score || score.composite_percentile).toFixed(0)}
        </span>
        <ConvictionBadge level={score.conviction_level} />
        <ActionPill
          signal={score.signal}
          buyPrice={score.buy_price}
          sellPrice={score.sell_price}
          actualPrice={score.actual_price}
        />
        {hasV2 && (
          <>
            {score.winning_track && (
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                score.winning_track === "compounder"
                  ? "bg-accent/10 text-accent"
                  : "bg-purple-500/10 text-purple-400"
              }`}>
                {score.winning_track === "compounder" ? "Compounder" : "Mispricing"} Track
              </span>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); setShowData(!showData) }}
              className="text-xs text-accent hover:text-accent/80 underline ml-2"
              data-testid="thesis-data-toggle"
            >
              {showData ? "Show Thesis" : "Show Data"}
            </button>
          </>
        )}
      </div>

      {hasV2 && score.asymmetry_ratio != null && (
        <div className="flex items-center gap-4 mb-4 text-sm">
          <span className="text-text-secondary">
            Asymmetry:{" "}
            <span className="text-text-primary font-bold">
              {score.asymmetry_ratio.toFixed(1)}x
            </span>
          </span>
          {score.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-medium">
                {score.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {score.timing_signal && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              score.timing_signal === "buy_now"
                ? "bg-bullish/10 text-bullish"
                : score.timing_signal === "add_on_pullback"
                  ? "bg-accent/10 text-accent"
                  : "bg-text-secondary/10 text-text-secondary"
            }`}>
              {score.timing_signal === "buy_now"
                ? "Buy now"
                : score.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </div>
      )}

      {/* Price Chart — full width */}
      <PriceChart
        bars={score.price_history ?? undefined}
        buyPrice={score.buy_price}
        sellPrice={score.sell_price}
        className="mb-6"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left column: Factor Breakdown */}
        <FactorBreakdown
          quality={score.quality}
          value={score.value}
          momentum={score.momentum}
          capitalAllocation={score.capital_allocation}
          catalyst={score.catalyst}
          winningTrack={score.winning_track}
          showAllFactors={showData}
        />

        {/* Right column: Filters + Metadata + Valuation + Signal History */}
        <div className="space-y-6">
          {score.filters_passed.length > 0 && (
            <FilterList filters={score.filters_passed} />
          )}

          {/* Metadata */}
          <div data-testid="asset-metadata">
            <h3 className="text-base font-semibold text-text-primary mb-3">
              Metadata
            </h3>
            <dl className="space-y-2 text-sm">
              {score.growth_stage && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Growth Stage</dt>
                  <dd className="text-text-primary">
                    {formatAttributeLabel(score.growth_stage)}
                  </dd>
                </div>
              )}
              {score.data_coverage !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Data Coverage</dt>
                  <dd className="text-text-primary">
                    {(score.data_coverage * 100).toFixed(0)}%
                  </dd>
                </div>
              )}
              {score.scored_at && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Scored At</dt>
                  <dd className="text-text-primary">
                    {formatScoredAt(score.scored_at)}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          <ValuationBreakdown
            methods={score.valuation_methods}
            intrinsicValue={score.intrinsic_value}
            actualPrice={score.actual_price}
            marginOfSafety={score.margin_of_safety}
            invalidReason={score.price_target_invalid_reason}
          />

          <SignalTimeline transitions={score.signal_history ?? undefined} />
        </div>
      </div>
    </div>
  )
}
