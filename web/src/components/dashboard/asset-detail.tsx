"use client"

import { useState, useMemo } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { ConvictionBadge } from "@/components/ui"
import { ActionPill } from "@/components/ui"
import { formatAttributeLabel, formatScoredAt } from "@/lib/format"
import { computeInstitutionalMetrics } from "@/lib/compute-institutional-metrics"
import { composeAiSummary } from "@/lib/compose-ai-summary"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import { PriceChart } from "./price-chart"
import { ValuationBreakdown } from "./valuation-breakdown"
import { SignalTimeline } from "./signal-timeline"
import { InstitutionalMetrics } from "./institutional-metrics"
import { AiSummary } from "./ai-summary"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetDetailProps {
  score: ScoreResponse
  className?: string
}

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export function AssetDetail({ score, className = "" }: AssetDetailProps) {
  const [showData, setShowData] = useState(false)
  const hasV2 = score.opportunity_type != null
  const prefersReduced = useReducedMotion()

  const institutionalMetrics = useMemo(
    () => computeInstitutionalMetrics(score),
    [score],
  )

  const aiSummary = useMemo(() => composeAiSummary(score), [score])

  function getTransition(delay: number) {
    if (prefersReduced) return { duration: 0 }
    return { duration: 0.4, ease: "easeOut" as const, delay }
  }

  return (
    <div
      className={`border-t border-border-primary pt-8 mt-4 asset-detail-ambient ${className}`}
      data-testid={`asset-detail-${score.ticker}`}
    >
      {/* Header */}
      <motion.div
        className="flex items-center gap-3 mb-8"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={getTransition(0)}
      >
        <h3 className="text-2xl font-bold tracking-tight text-text-primary">
          {score.ticker}
        </h3>
        <span className="text-sm font-normal text-text-tertiary">
          {score.name}
        </span>
        <span className="text-3xl font-mono font-bold text-accent ml-auto">
          {(score.score ?? score.composite_percentile).toFixed(0)}
        </span>
        <ConvictionBadge level={score.composite_tier} />
        <ActionPill
          signal={score.signal}
          buyPrice={score.buy_price}
          sellPrice={score.sell_price}
          actualPrice={score.actual_price}
        />
        {hasV2 && (
          <>
            {score.winning_track && (
              <span
                className={`text-xs px-2 py-0.5 rounded font-medium ${
                  score.winning_track === "compounder"
                    ? "bg-accent/10 text-accent"
                    : "bg-purple-500/10 text-purple-400"
                }`}
              >
                {score.winning_track === "compounder" ? "Compounder" : "Mispricing"} Track
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                setShowData(!showData)
              }}
              className="text-xs text-accent hover:text-accent/80 underline ml-2"
              data-testid="thesis-data-toggle"
            >
              {showData ? "Show Thesis" : "Show Data"}
            </button>
          </>
        )}
      </motion.div>

      {/* V2 Metrics Row */}
      {hasV2 && score.asymmetry_ratio != null && (
        <motion.div
          className="flex items-center gap-4 mb-6 text-sm"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          transition={getTransition(0.05)}
        >
          <span className="text-text-secondary">
            Asymmetry:{" "}
            <span className="text-text-primary font-mono font-bold">
              {score.asymmetry_ratio.toFixed(1)}x
            </span>
          </span>
          {score.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-mono font-medium">
                {score.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {score.timing_signal && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                score.timing_signal === "buy_now"
                  ? "bg-bullish/10 text-bullish"
                  : score.timing_signal === "add_on_pullback"
                    ? "bg-accent/10 text-accent"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
            >
              {score.timing_signal === "buy_now"
                ? "Buy now"
                : score.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </motion.div>
      )}

      {/* Hero Price Chart */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={getTransition(0.1)}
      >
        <PriceChart
          bars={score.price_history ?? undefined}
          buyPrice={score.buy_price}
          sellPrice={score.sell_price}
          className="mb-8"
        />
      </motion.div>

      {/* Institutional Metrics (Pro-gated) */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={getTransition(0.5)}
      >
        <InstitutionalMetrics metrics={institutionalMetrics} className="mb-8" />
      </motion.div>

      {/* AI Summary (Pro-gated) */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={getTransition(0.7)}
      >
        <AiSummary
          summary={aiSummary.summary}
          confidence={aiSummary.confidence}
          className="mb-8"
        />
      </motion.div>

      {/* Two-column layout: Factors | Right column */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-12 gap-8"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={getTransition(0.8)}
      >
        {/* Left column: Factor Breakdown (7 cols) */}
        <div className="md:col-span-7">
          <FactorBreakdown
            quality={score.quality}
            value={score.value}
            momentum={score.momentum}
            capitalAllocation={score.capital_allocation}
            catalyst={score.catalyst}
            winningTrack={score.winning_track}
            showAllFactors={showData}
          />
        </div>

        {/* Right column (5 cols) */}
        <div className="md:col-span-5 space-y-0">
          {score.filters_passed.length > 0 && (
            <div className="pb-5 mb-5 border-b border-border-primary/20">
              <FilterList filters={score.filters_passed} />
            </div>
          )}

          <div className="pb-5 mb-5 border-b border-border-primary/20">
            <ValuationBreakdown
              methods={score.valuation_methods}
              marginInvestValue={score.margin_invest_value}
              actualPrice={score.actual_price}
              marginOfSafety={score.margin_of_safety}
              invalidReason={score.price_target_invalid_reason}
            />
          </div>

          {/* Metadata */}
          <div className="pb-5 mb-5 border-b border-border-primary/20" data-testid="asset-metadata">
            <h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
              Metadata
            </h3>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              {score.growth_stage && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Growth Stage
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {formatAttributeLabel(score.growth_stage)}
                  </dd>
                </>
              )}
              {score.data_coverage !== undefined && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Data Coverage
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {(score.data_coverage * 100).toFixed(0)}%
                  </dd>
                </>
              )}
              {score.scored_at && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Scored At
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {formatScoredAt(score.scored_at)}
                  </dd>
                </>
              )}
            </div>
          </div>

          <SignalTimeline transitions={score.signal_history ?? undefined} />
        </div>
      </motion.div>
    </div>
  )
}
