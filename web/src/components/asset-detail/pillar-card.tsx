"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { formatAttributeLabel } from "@/lib/format"
import { SUB_FACTOR_FORMULAS } from "@/lib/sub-factor-formulas"
import { FormulaTooltip } from "@/components/ui/formula-tooltip"
import type { FactorBreakdownResponse } from "@/lib/api/types"

function normalizeSubFactorKey(name: string): string {
  return name.toLowerCase().replace(/[\s\-\u2013]+/g, "_").replace(/[^a-z0-9_]/g, "")
}

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

function getTierColor(p: number): string {
  if (p >= 80) return "var(--color-percentile-exceptional)"
  if (p >= 60) return "var(--color-percentile-strong)"
  if (p >= 40) return "var(--color-percentile-average)"
  if (p >= 20) return "var(--color-percentile-below)"
  return "var(--color-percentile-weak)"
}

export function PillarCard({ pillar }: PillarCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [expandedSub, setExpandedSub] = useState<string | null>(null)
  const name = pillar.factor_name.charAt(0).toUpperCase() + pillar.factor_name.slice(1)
  const weightPct = Math.round(pillar.weight * 100)
  const testId = `pillar-${pillar.factor_name}`
  const tierColor = getTierColor(pillar.average_percentile)

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
      data-testid={testId}
    >
      <div className="p-4 space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span
            className="text-label-sm"
            style={{ color: "var(--color-on-surface-variant)" }}
          >
            {name.toUpperCase()}
          </span>
          <span
            className="text-label-sm"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            {weightPct}%
          </span>
        </div>

        {/* Percentile */}
        <div className="text-center py-2">
          <span
            className="text-mono-data leading-none"
            style={{ color: tierColor }}
          >
            {Math.round(pillar.average_percentile)}
          </span>
          <span
            className="text-label-sm block mt-1"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            percentile
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 rounded-sm" style={{ background: "var(--color-surface-container-lowest)" }}>
          <div
            className="h-full rounded-sm transition-all duration-500"
            style={{ width: `${pillar.average_percentile}%`, background: tierColor }}
          />
        </div>

        {/* Toggle */}
        <button
          className="flex items-center gap-1 text-xs hover:opacity-80 transition-opacity w-full justify-center pt-1"
          style={{ color: "var(--color-text-tertiary)" }}
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
            <div className="px-4 py-3 space-y-2">
              {/* Table header */}
              <div
                className="grid grid-cols-[1fr_80px_60px_60px] gap-2 text-label-sm"
                style={{ color: "var(--color-text-tertiary)" }}
              >
                <span>Factor</span>
                <span className="text-right">Raw</span>
                <span className="text-right">Pctile</span>
                <span className="text-right">Rating</span>
              </div>
              {pillar.sub_scores.map((sub, idx) => {
                const formulaData = SUB_FACTOR_FORMULAS[sub.name]
                const isSubExpanded = expandedSub === sub.name
                const rowBg = idx % 2 === 0 ? "var(--color-surface)" : "var(--color-surface-container-lowest)"
                return (
                  <div key={sub.name}>
                    <div
                      className={`grid grid-cols-[1fr_80px_60px_60px] gap-2 text-xs items-center rounded px-1 py-0.5 ${formulaData ? "cursor-pointer" : ""}`}
                      style={{ background: rowBg }}
                      onClick={() =>
                        formulaData && setExpandedSub(isSubExpanded ? null : sub.name)
                      }
                    >
                      <span className="truncate" style={{ color: "var(--color-on-surface)" }}>
                        <FormulaTooltip metricKey={normalizeSubFactorKey(sub.name)}>
                          <span>{formatAttributeLabel(sub.name)}</span>
                        </FormulaTooltip>
                        {formulaData && (
                          <span className="text-[9px] ml-1" style={{ color: "var(--color-text-tertiary)" }}>
                            {isSubExpanded ? "\u25B2" : "fx"}
                          </span>
                        )}
                      </span>
                      <span className="text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
                        {typeof sub.raw_value === "number"
                          ? sub.raw_value % 1 === 0
                            ? sub.raw_value
                            : sub.raw_value.toFixed(2)
                          : sub.raw_value}
                      </span>
                      <span className="text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                        {Math.round(sub.percentile_rank)}th
                      </span>
                      <span className="text-right" style={{ color: "var(--color-text-tertiary)" }}>
                        {sub.detail || getPercentileDetail(sub.percentile_rank)}
                      </span>
                    </div>
                    {isSubExpanded && formulaData && (
                      <div
                        className="text-xs pl-2 py-1 ml-1 mb-1"
                        style={{
                          color: "var(--color-text-tertiary)",
                          borderLeft: "2px solid color-mix(in srgb, var(--color-primary-muted) 30%, transparent)",
                        }}
                      >
                        <span style={{ fontFamily: "var(--font-data)" }}>{formulaData.formula}</span>
                        <span className="italic ml-2">&mdash; {formulaData.source}</span>
                      </div>
                    )}
                  </div>
                )
              })}
              <p className="text-xs pt-2" style={{ color: "var(--color-text-tertiary)" }}>
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
