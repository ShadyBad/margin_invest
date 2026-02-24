"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { PillarCard } from "./pillar-card"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface HypotheticalScoresProps {
  ticker: string
  compositeScore: number
  compositePercentile: number
  convictionLevel: string
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  growthStage?: string | null
}

const CONVICTION_MINIMUM = 65.0

export function HypotheticalScores({
  ticker,
  compositeScore,
  compositePercentile,
  convictionLevel,
  quality,
  value,
  momentum,
}: HypotheticalScoresProps) {
  const [expanded, setExpanded] = useState(false)
  const wouldQualify = compositeScore >= CONVICTION_MINIMUM

  const narrative = wouldQualify
    ? `Even if it had passed filters, ${ticker} would rank in the ${Math.round(compositePercentile)}th percentile of the scored universe. However, the elimination filters exist to remove fundamental risk regardless of scoring potential.`
    : `Even if it had passed filters, ${ticker} would rank in the ${Math.round(compositePercentile)}th percentile of the scored universe — below the threshold for any conviction level (minimum: ${CONVICTION_MINIMUM}).`

  return (
    <section data-testid="hypothetical-scores">
      <button
        className="w-full terminal-card px-4 py-3 text-left flex items-center gap-2 hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
        data-testid="hypothetical-toggle"
      >
        <span className="text-sm text-text-tertiary">{expanded ? "\u25B2" : "\u25BC"}</span>
        <span className="text-sm text-text-secondary">
          What if {ticker} had passed all filters?
        </span>
        <span className="text-xs text-text-tertiary ml-auto">See partial scores</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
            data-testid="hypothetical-content"
          >
            <div className="mt-3 space-y-4">
              {/* Warning banner */}
              <div className="border border-warning/30 bg-warning/5 rounded-lg px-4 py-3">
                <span className="text-sm font-semibold text-warning block">
                  HYPOTHETICAL SCORES
                </span>
                <p className="text-xs text-text-secondary mt-1">
                  These scores are informational only. {ticker} did not survive elimination
                  and is NOT a scored recommendation.
                </p>
              </div>

              {/* Summary */}
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className="text-text-tertiary text-xs block">Composite Score</span>
                  <span className="text-text-primary font-mono">
                    {compositeScore.toFixed(1)}
                  </span>
                </div>
                <div>
                  <span className="text-text-tertiary text-xs block">Conviction</span>
                  <span className="text-text-primary uppercase">{convictionLevel}</span>
                </div>
                <div>
                  <span className="text-text-tertiary text-xs block">Signal</span>
                  <span className="text-text-tertiary">N/A</span>
                </div>
              </div>

              {/* Pillar cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <PillarCard pillar={quality} />
                <PillarCard pillar={value} />
                <PillarCard pillar={momentum} />
              </div>

              {/* Narrative conclusion */}
              <p className="text-xs text-text-secondary leading-relaxed border-t border-white/[0.06] pt-3">
                {narrative}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
