"use client"

import { motion } from "framer-motion"
import { ScoreBreakdownBars } from "../visuals/score-breakdown-bars"

const ease = [0.22, 1, 0.36, 1] as const

const pillars = [
  {
    name: "Quality",
    desc: "Measures the durability and efficiency of a business \u2014 how well it converts capital into returns, and whether those returns are real.",
    factors: [
      "ROIC-WACC Spread",
      "ROIC Stability",
      "Incremental ROIC",
      "Gross Profitability",
      "Piotroski F-Score",
      "Accrual Ratio",
      "Moat Durability",
    ],
  },
  {
    name: "Value",
    desc: "Measures what you\u2019re paying relative to what the business generates \u2014 across multiple valuation lenses to avoid single-metric traps.",
    factors: [
      "DCF Margin of Safety",
      "EV/FCF",
      "Acquirer\u2019s Multiple",
      "Owner Earnings Yield",
      "Shareholder Yield",
      "Reverse DCF Growth Gap",
      "Asset Floor",
    ],
  },
  {
    name: "Momentum",
    desc: "Measures whether the market, insiders, and institutions are confirming what the fundamentals suggest.",
    factors: [
      "Price Momentum (12\u20111 month)",
      "Standardized Unexpected Earnings",
      "Insider Cluster Score",
      "Institutional Accumulation",
      "Sentiment Score",
      "Runway Score",
    ],
  },
]

export function ScoringSection() {
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
          Multi-Factor Scoring
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          20+ factors. Three pillars. Sector-neutral ranking.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Every stock that passes elimination is scored across 20+ quantitative
          factors organized into three pillars. Each factor is ranked within its own
          sector first — a tech company&apos;s profitability is compared to other tech
          companies, not to utilities. This sector-neutral approach ensures scores
          reflect genuine outlier performance among true peers.
        </motion.p>

        {/* Pillar cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {pillars.map((pillar, i) => (
            <motion.div
              key={pillar.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated border-t-2 border-t-accent"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[18px] font-semibold text-accent mb-3">
                {pillar.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed mb-4">
                {pillar.desc}
              </p>
              <div className="space-y-1">
                {pillar.factors.map((factor) => (
                  <span
                    key={factor}
                    className="block text-[12px] text-text-tertiary font-mono"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* How scoring works */}
        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Factor scores are converted to percentile ranks within each sector, then
          combined into a pillar average. Pillar weights adjust based on the
          company&apos;s growth stage — a high-growth company is weighted differently
          than a mature cash cow. The final composite score is re-ranked across the
          entire universe to produce a single conviction percentile.
        </motion.p>

        {/* Score breakdown visual */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
          className="max-w-lg"
        >
          <ScoreBreakdownBars />
        </motion.div>
      </div>
    </section>
  )
}
