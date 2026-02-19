"use client"

import { useState, useMemo, useEffect, useCallback } from "react"
import { createPortal } from "react-dom"
import { AnimatePresence, motion } from "framer-motion"
import { PanelBackdrop } from "./panel-backdrop"
import { ExecutiveHeader } from "./executive-header"
import { ScoreChart } from "./score-chart"
import { PriceTargetChart } from "./price-target-chart"
import { PanelFactorBreakdown } from "./panel-factor-breakdown"
import { KpiGrid } from "./kpi-grid"
import { InsightPanel } from "./insight-panel"
import { PanelValuation } from "./panel-valuation"
import { PanelFilterList } from "./panel-filter-list"
import { ScoreHistoryTable } from "./score-history-table"
import { ProGate } from "../pro-gate"
import { composeAiSummary } from "@/lib/compose-ai-summary"
import type { TimeRange } from "./time-range-selector"
import type { ScoreResponse, InstitutionalMetricsResponse, ScoreHistoryResponse } from "@/lib/api/types"
import { getScoreHistory } from "@/lib/api/scores"

interface AssetPanelProps {
  isOpen: boolean
  onClose: () => void
  ticker: string
  scoredResult: ScoreResponse
  metrics: InstitutionalMetricsResponse | null
}

const PANEL_EASE = [0.22, 1, 0.36, 1] as const

function computeInsights(score: ScoreResponse) {
  const strengths: string[] = []
  const risks: string[] = []

  const factors = [
    { name: "quality", p: score.quality.average_percentile },
    { name: "value", p: score.value.average_percentile },
    { name: "momentum", p: score.momentum.average_percentile },
  ]

  for (const f of factors) {
    if (f.p >= 80) {
      strengths.push(`Exceptional ${f.name} — top ${100 - Math.round(f.p)}% on key metrics`)
    } else if (f.p >= 60) {
      strengths.push(`Strong ${f.name} with ${Math.round(f.p)}th percentile ranking`)
    }
    if (f.p < 40) {
      risks.push(`Weak ${f.name} at ${Math.round(f.p)}th percentile`)
    }
  }

  for (const filter of score.filters_passed) {
    if (!filter.passed) {
      risks.push(`${filter.name.replace(/_/g, " ")} filter failed`)
    }
  }

  if (strengths.length === 0) strengths.push("Balanced factor profile across all dimensions")
  if (risks.length === 0) risks.push("No significant risk flags identified")

  return { strengths, risks }
}

export function AssetPanel({ isOpen, onClose, ticker, scoredResult, metrics }: AssetPanelProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("3M")
  const [historyData, setHistoryData] = useState<ScoreHistoryResponse | null>(null)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose()
  }, [onClose])

  useEffect(() => {
    if (!isOpen) return
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, handleKeyDown])

  useEffect(() => {
    if (!isOpen || !ticker) return
    let cancelled = false
    getScoreHistory(ticker)
      .then((data) => {
        if (!cancelled) setHistoryData(data)
      })
      .catch(() => {
        // Silently fail — synthetic fallback will be used
      })
    return () => { cancelled = true }
  }, [isOpen, ticker])

  const aiSummary = useMemo(() => composeAiSummary(scoredResult), [scoredResult])
  const insights = useMemo(() => computeInsights(scoredResult), [scoredResult])

  const scoreHistory = useMemo(() => {
    if (historyData && historyData.points.length > 0) {
      return historyData.points.map((p) => ({
        date: p.scored_at,
        score: p.composite_percentile,
        delta: p.delta ?? 0,
        signal: p.signal,
        conviction: p.conviction_level,
        keyChange: p.delta != null ? `${p.delta > 0 ? "+" : ""}${p.delta.toFixed(1)}` : "Current",
      }))
    }
    return [{
      date: scoredResult.scored_at ?? new Date().toISOString(),
      score: scoredResult.score,
      delta: 0,
      signal: scoredResult.signal,
      conviction: scoredResult.conviction_level,
      keyChange: "Current",
    }]
  }, [historyData, scoredResult])

  const scoreChartData = useMemo(() => {
    if (historyData && historyData.points.length > 0) {
      return historyData.points.map((p) => ({
        date: p.scored_at,
        score: p.composite_percentile,
        signal: p.signal,
      }))
    }
    return [{
      date: scoredResult.scored_at ?? new Date().toISOString(),
      score: scoredResult.score,
      signal: scoredResult.signal,
    }]
  }, [historyData, scoredResult])

  const latestDelta = useMemo(() => {
    if (historyData && historyData.points.length >= 2) {
      return historyData.points[historyData.points.length - 1].delta
    }
    return null
  }, [historyData])

  const priceHistoryForChart = useMemo(() => {
    if (!scoredResult.price_history || scoredResult.price_history.length === 0) return undefined
    return scoredResult.price_history.map((bar) => ({
      date: bar.date,
      close: bar.close,
    }))
  }, [scoredResult.price_history])

  const universeRank = scoredResult.universe_percentile >= 90
    ? `Top ${100 - Math.round(scoredResult.universe_percentile)}% of universe`
    : `${Math.round(scoredResult.universe_percentile)}th percentile`

  if (typeof window === "undefined") return null

  const content = (
    <AnimatePresence>
      {isOpen && (
        <div data-testid="asset-panel" className="fixed inset-0 z-50">
          <PanelBackdrop onClose={onClose} />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={`${ticker} analysis panel`}
            className="fixed top-0 right-0 bottom-0 w-[70vw] min-w-[900px] max-w-[1200px] bg-[#0B0D10] shadow-[0_0_80px_rgba(0,0,0,0.6)] overflow-y-auto z-50"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.4, ease: PANEL_EASE }}
          >
            <ExecutiveHeader
              ticker={ticker}
              companyName={scoredResult.name}
              compositeScore={scoredResult.score}
              scoreDelta={latestDelta ?? 0}
              conviction={scoredResult.conviction_level}
              signal={scoredResult.signal}
              opportunityType={(scoredResult.winning_track as "compounder" | "mispricing") ?? "compounder"}
              buyPrice={scoredResult.buy_price}
              sellPrice={scoredResult.sell_price}
              actualPrice={scoredResult.actual_price}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              onClose={onClose}
            />

            {/* 2-column body */}
            <div className="grid grid-cols-[1fr_0.67fr]">
              {/* Left column — 60% */}
              <div className="border-r border-white/[0.06]">
                <ScoreChart
                  data={scoreChartData}
                  timeRange={timeRange}
                  showBenchmark={false}
                  universeRank={universeRank}
                  scoringFrequency="Scored weekly"
                  lastScored={scoredResult.scored_at ? "Recent" : undefined}
                />
                {historyData && historyData.points.length > 0 && (
                  <PriceTargetChart
                    scoreHistory={historyData.points}
                    priceHistory={priceHistoryForChart}
                  />
                )}
                <PanelFactorBreakdown
                  quality={scoredResult.quality}
                  value={scoredResult.value}
                  momentum={scoredResult.momentum}
                  capitalAllocation={scoredResult.capital_allocation}
                  catalyst={scoredResult.catalyst}
                  winningTrack={scoredResult.winning_track}
                />
              </div>

              {/* Right column — 40% */}
              <div className="p-6 space-y-6">
                <ProGate>
                  <KpiGrid
                    sharpeRatio={metrics?.sharpe_ratio?.value ?? null}
                    maxDrawdown={metrics?.max_drawdown?.value ?? null}
                    volatility={metrics?.volatility?.value ?? null}
                    avgProfitMargin={metrics?.avg_profit_margin?.value ?? null}
                    allocationWeight={metrics?.allocation_weight?.value ?? null}
                    marginOfSafety={metrics?.margin_of_safety?.value != null ? Math.round(metrics.margin_of_safety.value * 100) : null}
                  />
                </ProGate>

                <ProGate>
                  <InsightPanel
                    strengths={insights.strengths}
                    risks={insights.risks}
                    commentary={aiSummary.summary}
                    confidence={aiSummary.confidence}
                  />
                </ProGate>

                <PanelValuation
                  intrinsicValue={scoredResult.margin_invest_value}
                  currentPrice={scoredResult.actual_price}
                  marginOfSafety={scoredResult.margin_of_safety}
                  methods={scoredResult.valuation_methods}
                  buyBelow={scoredResult.buy_price}
                  sellPrice={scoredResult.sell_price}
                />

                <PanelFilterList filters={scoredResult.filters_passed} />
              </div>
            </div>

            {/* Full-width bottom */}
            <div className="border-t border-white/[0.06]">
              <ScoreHistoryTable history={scoreHistory} />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )

  return createPortal(content, document.body)
}
