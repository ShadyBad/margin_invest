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
        <h3 className="text-[14px] font-semibold text-[#E8E6E3]">Filters</h3>
        <span className="text-[12px] font-mono text-[#9A9590] bg-white/[0.04] px-2 py-0.5 rounded">
          {passCount}/{filters.length}
        </span>
      </div>
      <div className="space-y-0.5">
        {filters.map((filter) => {
          const isExpanded = expanded.has(filter.name)
          return (
            <div key={filter.name}>
              <div
                className={`flex items-center gap-2 h-8 px-2 rounded cursor-pointer transition-colors duration-150 hover:bg-white/[0.03] ${
                  !filter.passed ? "bg-[rgba(199,75,80,0.04)]" : ""
                }`}
                data-testid={`panel-filter-${filter.name}`}
                onClick={() => toggle(filter.name)}
              >
                <span className={`text-[14px] shrink-0 ${filter.passed ? "text-[#1A7A5A]" : "text-[#C74B50]"}`}>
                  {filter.passed ? "\u2713" : "\u2717"}
                </span>
                <span className="text-[13px] text-[#E8E6E3]">{formatAttributeLabel(filter.name)}</span>
                <span className="text-[11px] font-mono text-[#5C5955] ml-auto">
                  {filter.passed ? "PASS" : "FAIL"}
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
                    <p className="text-[11px] font-mono text-[#5C5955] px-2 pb-2 pl-7">
                      {filter.detail}
                    </p>
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
