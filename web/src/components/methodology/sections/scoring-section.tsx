"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ScoreBreakdownBars } from "../visuals/score-breakdown-bars"

const ease = [0.22, 1, 0.36, 1] as const

const pillars = [
  {
    name: "Quality",
    count: 7,
    desc: "Measures the durability and efficiency of a business — how well it converts capital into returns, and whether those returns are real.",
    borderColor: "border-t-accent",
    titleColor: "text-accent",
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
    count: 7,
    desc: "Measures what you're paying relative to what the business generates — across multiple valuation lenses to avoid single-metric traps.",
    borderColor: "border-t-bullish",
    titleColor: "text-bullish",
    factors: [
      "DCF Margin of Safety",
      "EV/FCF",
      "Acquirer's Multiple",
      "Owner Earnings Yield",
      "Shareholder Yield",
      "Reverse DCF Growth Gap",
      "Asset Floor",
    ],
  },
  {
    name: "Momentum",
    count: 6,
    desc: "Measures whether the market, insiders, and institutions are confirming what the fundamentals suggest.",
    borderColor: "border-t-warning",
    titleColor: "text-warning",
    factors: [
      "Price Momentum (12‑1 month)",
      "Standardized Unexpected Earnings",
      "Insider Cluster Score",
      "Institutional Accumulation",
      "Sentiment Score",
      "Runway Score",
    ],
  },
]

export function ScoringSection() {
  const [expandedPillar, setExpandedPillar] = useState<string | null>(null)

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
          Stage 3 · Factor Scoring
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          20 factors. Three pillars. Sector-neutral ranking.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          AAPL passed all filters. Now it enters multi-factor scoring across
          three pillars. Each factor is ranked within AAPL&apos;s GICS sector.
          A percentile of 85 means AAPL scores better than 85% of its
          tech-sector peers on that factor.
        </motion.p>

        {/* Pillar cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {pillars.map((pillar, i) => (
            <motion.div
              key={pillar.name}
              className={`border border-border-primary rounded-lg bg-bg-elevated border-t-2 ${pillar.borderColor} overflow-hidden`}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <button
                type="button"
                className="w-full p-6 text-left"
                onClick={() =>
                  setExpandedPillar(
                    expandedPillar === pillar.name ? null : pillar.name
                  )
                }
              >
                <div className="flex items-center justify-between mb-3">
                  <h3
                    className={`text-[18px] font-semibold ${pillar.titleColor}`}
                  >
                    {pillar.name}
                  </h3>
                  <span className="text-[13px] font-mono text-text-tertiary">
                    {pillar.count} factors
                  </span>
                </div>
                <p className="text-[14px] text-text-secondary leading-relaxed">
                  {pillar.desc}
                </p>
              </button>
              {expandedPillar === pillar.name && (
                <div className="px-6 pb-5 pt-0">
                  <div className="border-t border-border-subtle pt-3 space-y-1">
                    {pillar.factors.map((factor) => (
                      <span
                        key={factor}
                        className="block text-[12px] text-text-tertiary font-mono"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
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
          Factor scores are converted to percentile ranks within each sector,
          then combined into a pillar average. Pillar weights adjust based on
          the company&apos;s growth stage — a high-growth company is weighted
          differently than a mature cash cow. The final composite score is
          re-ranked across the entire universe to produce a single composite
          percentile.
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
