"use client"

import { motion } from "framer-motion"
import { FilterFunnel } from "../visuals/filter-funnel"

const ease = [0.22, 1, 0.36, 1] as const

const filters = [
  {
    name: "Liquidity",
    desc: "Sufficient trading volume and market cap to build a real position",
  },
  {
    name: "Earnings Quality",
    desc: "Beneish M-Score screens for signs of earnings manipulation",
  },
  {
    name: "Bankruptcy Risk",
    desc: "Altman Z-Score identifies companies in financial distress",
  },
  {
    name: "Cash Flow",
    desc: "Consistent free cash flow generation over multiple years",
  },
  {
    name: "Interest Coverage",
    desc: "Ability to service debt obligations from operating earnings",
  },
  {
    name: "Balance Sheet Health",
    desc: "Current ratio and quick ratio above sector-adjusted thresholds",
  },
]

export function FiltersSection() {
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
          Elimination Filters
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Bad candidates are removed before scoring begins.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Before any stock receives a score, it must pass six independent elimination
          filters. All six run regardless of earlier failures — you see the full
          diagnostic, not just the first thing that went wrong. Roughly 40% of the
          universe fails at least one filter.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {filters.map((filter, i) => (
            <motion.div
              key={filter.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {filter.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {filter.desc}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
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
          Filter thresholds are sector-adjusted — a utility company and a tech company
          are held to different standards where appropriate.
        </motion.p>
      </div>
    </section>
  )
}
