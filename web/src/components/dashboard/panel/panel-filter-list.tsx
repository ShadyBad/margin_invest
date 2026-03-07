"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { formatAttributeLabel } from "@/lib/format"
import type { FilterResultResponse } from "@/lib/api/types"

interface PanelFilterListProps {
  filters: FilterResultResponse[]
}

export function PanelFilterList({ filters }: PanelFilterListProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const passCount = filters.filter((f) => f.passed).length
  const inconclusiveCount = filters.filter((f) => f.verdict === "inconclusive").length

  function toggle(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div data-testid="panel-filter-list">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-semibold text-text-primary">Filters</h3>
        <div className="flex items-center gap-1.5">
          {inconclusiveCount > 0 && (
            <span className="text-[11px] font-mono text-amber-500/70 bg-[rgba(217,167,50,0.06)] px-1.5 py-0.5 rounded">
              {inconclusiveCount} inconclusive
            </span>
          )}
          <span className="text-[12px] font-mono text-text-secondary bg-surface-overlay px-2 py-0.5 rounded">
            {passCount}/{filters.length}
          </span>
        </div>
      </div>
      <div className="space-y-0.5">
        {filters.map((filter) => {
          const isExpanded = expanded.has(filter.name)
          const isInconclusive = filter.verdict === "inconclusive"
          const icon = isInconclusive ? "?" : filter.passed ? "\u2713" : "\u2717"
          const iconColor = isInconclusive
            ? "text-amber-500"
            : filter.passed
              ? "text-bullish"
              : "text-bearish"
          const statusLabel = isInconclusive ? "INCONCLUSIVE" : filter.passed ? "PASS" : "FAIL"
          const statusColor = isInconclusive ? "text-amber-500/70" : "text-text-tertiary"
          const rowBg = isInconclusive
            ? "bg-[rgba(217,167,50,0.04)]"
            : !filter.passed
              ? "bg-[rgba(199,75,80,0.04)]"
              : ""

          return (
            <div key={filter.name}>
              <div
                className={`flex items-center gap-2 h-8 px-2 rounded cursor-pointer transition-colors duration-150 hover:bg-surface-overlay ${rowBg}`}
                data-testid={`panel-filter-${filter.name}`}
                onClick={() => toggle(filter.name)}
              >
                <span className={`text-[14px] shrink-0 ${iconColor}`}>{icon}</span>
                <span className="text-[13px] text-text-primary">
                  {formatAttributeLabel(filter.name)}
                </span>
                <span className={`text-[11px] font-mono ml-auto ${statusColor}`}>
                  {statusLabel}
                </span>
              </div>
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    {isInconclusive && (
                      <p className="text-[11px] font-mono text-amber-500/70 px-2 pb-1 pl-7">
                        Cannot assess — insufficient data
                      </p>
                    )}
                    {isInconclusive &&
                      filter.missing_fields &&
                      filter.missing_fields.length > 0 && (
                        <p className="text-[10px] font-mono text-amber-500/50 px-2 pb-1 pl-7">
                          Missing: {filter.missing_fields.join(", ")}
                        </p>
                      )}
                    {filter.detail && (
                      <p className="text-[11px] font-mono text-text-tertiary px-2 pb-2 pl-7">
                        {filter.detail}
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}
