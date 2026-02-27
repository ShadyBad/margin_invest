"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { FilterFunnel } from "../visuals/filter-funnel"

const ease = [0.22, 1, 0.36, 1] as const

const aaplFilters = [
  {
    name: "Beneish M-Score",
    value: "\u22122.41",
    threshold: "< \u22121.78",
    pass: true,
    detail:
      "Screens for earnings manipulation. A score below \u22121.78 indicates the company is unlikely to be a manipulator.",
  },
  {
    name: "Altman Z-Score",
    value: "5.12",
    threshold: "> 1.1",
    pass: true,
    detail:
      "Predicts bankruptcy probability. Scores above 2.99 are in the safe zone; AAPL is well above.",
  },
  {
    name: "Current Ratio",
    value: "1.07",
    threshold: "> 0.8 (tech sector)",
    pass: true,
    detail:
      "Measures short-term liquidity. The threshold is sector-adjusted \u2014 tech companies typically carry less working capital.",
  },
  {
    name: "Interest Coverage",
    value: "29.8\u00d7",
    threshold: "> 5.0\u00d7 (tech sector)",
    pass: true,
    detail:
      "Operating earnings divided by interest expense. AAPL covers its debt obligations nearly 30 times over.",
  },
  {
    name: "FCF Distress",
    value: "5/5 years positive",
    threshold: "\u2265 3/5",
    pass: true,
    detail:
      "Checks whether the company generated positive free cash flow in at least 3 of the past 5 years.",
  },
  {
    name: "Liquidity",
    value: "$2.7T market cap",
    threshold: "> $300M",
    pass: true,
    detail:
      "Ensures sufficient market capitalization for meaningful institutional positioning and reliable price discovery.",
  },
]

export function FiltersSection() {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <section className="border-t border-border-subtle">
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Stage 2 · Elimination Filters
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Six binary checks. One failure means elimination.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          AAPL faces six binary pass/fail checks. One failure means immediate
          elimination — no exceptions, no overrides. All six run regardless
          of earlier failures so you see the full diagnostic, not just the
          first thing that went wrong.
        </motion.p>

        {/* AAPL filter results */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {aaplFilters.map((filter, i) => (
            <motion.div
              key={filter.name}
              className="border border-border-primary rounded-lg bg-bg-elevated overflow-hidden"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <button
                type="button"
                className="w-full p-5 text-left"
                onClick={() =>
                  setExpanded(
                    expanded === filter.name ? null : filter.name
                  )
                }
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-[15px] font-semibold text-text-primary">
                    {filter.name}
                  </h3>
                  <span className="text-[13px] font-mono text-bullish">
                    PASS
                  </span>
                </div>
                <div className="flex items-baseline gap-3">
                  <span className="text-[14px] font-mono text-text-primary">
                    {filter.value}
                  </span>
                  <span className="text-[12px] text-text-tertiary">
                    threshold: {filter.threshold}
                  </span>
                </div>
              </button>
              {expanded === filter.name && (
                <div className="px-5 pb-5 pt-0">
                  <p className="text-[13px] text-text-secondary leading-relaxed border-t border-border-subtle pt-3">
                    {filter.detail}
                  </p>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Result callout */}
        <motion.div
          className="p-5 border border-border-primary rounded-lg bg-bg-elevated mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p className="text-[15px] text-text-primary font-medium">
            <span className="text-bullish font-mono mr-2">6/6</span>
            AAPL passes all six filters and advances to scoring.
          </p>
          <p className="text-[12px] text-text-tertiary mt-1">
            Roughly 40% of the universe fails at least one filter and is
            eliminated before scoring begins.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.14, ease }}
        >
          <FilterFunnel />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.18, ease }}
        >
          Filter thresholds are sector-adjusted — a utility company and a tech
          company are held to different standards where appropriate.
        </motion.p>
      </div>
    </section>
  )
}
