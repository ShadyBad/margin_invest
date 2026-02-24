"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { formatAttributeLabel } from "@/lib/format"
import { SUB_FACTOR_FORMULAS } from "@/lib/sub-factor-formulas"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface PillarCardProps {
  pillar: FactorBreakdownResponse
}

function getPercentileDetail(p: number): string {
  if (p >= 80) return "Strong"
  if (p >= 60) return "Above avg"
  if (p >= 40) return "Average"
  if (p >= 20) return "Below avg"
  return "Weak"
}

export function PillarCard({ pillar }: PillarCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [expandedSub, setExpandedSub] = useState<string | null>(null)
  const name = pillar.factor_name.charAt(0).toUpperCase() + pillar.factor_name.slice(1)
  const weightPct = Math.round(pillar.weight * 100)
  const testId = `pillar-${pillar.factor_name}`

  return (
    <div className="terminal-card overflow-hidden" data-testid={testId}>
      <div className="p-4 space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-text-primary uppercase">{name}</span>
          <span className="text-xs font-mono text-text-tertiary">{weightPct}%</span>
        </div>

        {/* Percentile */}
        <div className="text-center py-2">
          <span className="text-3xl font-display text-text-primary leading-none">
            {Math.round(pillar.average_percentile)}
          </span>
          <span className="text-xs text-text-tertiary block mt-1">percentile</span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${pillar.average_percentile}%` }}
          />
        </div>

        {/* Toggle */}
        <button
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors w-full justify-center pt-1"
          onClick={() => setExpanded(!expanded)}
          data-testid={`${testId}-toggle`}
        >
          <span>{expanded ? "\u25B2" : "\u25BC"}</span>
          <span>{pillar.sub_scores.length} sub-factors</span>
        </button>
      </div>

      {/* Expanded sub-factors */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/[0.06] px-4 py-3 space-y-2">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_80px_60px_60px] gap-2 text-[10px] uppercase tracking-wider text-text-tertiary">
                <span>Factor</span>
                <span className="text-right">Raw</span>
                <span className="text-right">Pctile</span>
                <span className="text-right">Rating</span>
              </div>
              {pillar.sub_scores.map((sub) => {
                const formulaData = SUB_FACTOR_FORMULAS[sub.name]
                const isSubExpanded = expandedSub === sub.name
                return (
                  <div key={sub.name}>
                    <div
                      className={`grid grid-cols-[1fr_80px_60px_60px] gap-2 text-xs items-center ${formulaData ? "cursor-pointer hover:bg-white/[0.02] -mx-1 px-1 rounded" : ""}`}
                      onClick={() =>
                        formulaData && setExpandedSub(isSubExpanded ? null : sub.name)
                      }
                    >
                      <span className="text-text-primary truncate">
                        {formatAttributeLabel(sub.name)}
                        {formulaData && (
                          <span className="text-[9px] text-text-tertiary ml-1">
                            {isSubExpanded ? "\u25B2" : "fx"}
                          </span>
                        )}
                      </span>
                      <span className="text-right font-mono text-text-secondary">
                        {typeof sub.raw_value === "number"
                          ? sub.raw_value % 1 === 0
                            ? sub.raw_value
                            : sub.raw_value.toFixed(2)
                          : sub.raw_value}
                      </span>
                      <span className="text-right font-mono text-text-primary">
                        {Math.round(sub.percentile_rank)}th
                      </span>
                      <span className="text-right text-text-tertiary">
                        {sub.detail || getPercentileDetail(sub.percentile_rank)}
                      </span>
                    </div>
                    {isSubExpanded && formulaData && (
                      <div className="text-[10px] text-text-tertiary pl-2 py-1 border-l-2 border-accent/30 ml-1 mb-1">
                        <span className="font-mono">{formulaData.formula}</span>
                        <span className="italic ml-2">&mdash; {formulaData.source}</span>
                      </div>
                    )}
                  </div>
                )
              })}
              <p className="text-[10px] text-text-tertiary pt-2 border-t border-white/[0.04]">
                Each sub-factor is ranked within the stock&apos;s GICS sector first (sector-neutral),
                then combined.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
