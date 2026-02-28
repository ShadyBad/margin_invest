"use client"

import { motion } from "framer-motion"
import { CandidateJourneyChart } from "../visuals/candidate-journey-chart"

const ease = [0.22, 1, 0.36, 1] as const

const trackA = {
  name: "Track A — Compounder",
  desc: "Identifies businesses with durable competitive advantages and strong reinvestment engines — the kind that compounds value over long holding periods.",
  gates: [
    {
      label: "Moat Evidence",
      detail: "Multiple structural signals of a durable competitive advantage",
    },
    {
      label: "Reinvestment Engine",
      detail:
        "Retained earnings are being deployed at high incremental returns",
    },
    {
      label: "Capital Allocation",
      detail:
        "Management allocates capital with discipline — buybacks, dividends, or reinvestment",
    },
    {
      label: "Valuation/Growth Gap",
      detail:
        "The stock's price doesn't already reflect perfection — room for upside exists",
    },
  ],
}

const trackB = {
  name: "Track B — Mispricing",
  desc: "Identifies stocks trading at a significant discount to intrinsic value with a catalyst to close the gap.",
  gates: [
    {
      label: "Ensemble Valuation",
      detail:
        "Multiple valuation methods agree the stock is cheap — not just one ratio",
    },
    {
      label: "Downside Protection",
      detail: "A floor exists on how much you can lose — asset backing or cash flow stability",
    },
    {
      label: "Catalyst",
      detail:
        "Insider buying, institutional accumulation, or earnings momentum to trigger re-rating",
    },
    {
      label: "Quality Floor",
      detail:
        "Cheap for a reason doesn't qualify — a minimum quality bar must be met",
    },
  ],
}

const convictionLevels = [
  {
    level: "EXCEPTIONAL",
    meaning: "Qualifies on both tracks simultaneously — strongest composite tier",
  },
  {
    level: "HIGH",
    meaning:
      "Strong multi-factor case with clear margin of safety on one track",
  },
  {
    level: "WATCHLIST",
    meaning: "Promising alignment but one gate is weak — monitor for improvement",
  },
  {
    level: "NONE",
    meaning: "Does not meet the threshold on either track",
  },
]

export function ConvictionSection() {
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
          Stage 4 · Dual-Track Scoring
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Two independent lenses. Multiplicative scoring.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          With factor scores in hand, AAPL enters the dual-track scoring
          system. Each track has four gates, and scoring is multiplicative —
          one weak gate kills the score. A company can&apos;t compensate for a
          missing moat with cheap valuation.
        </motion.p>

        {/* Track cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {[trackA, trackB].map((track, i) => (
            <motion.div
              key={track.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                {track.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed mb-4">
                {track.desc}
              </p>
              <p className="text-[12px] font-medium text-text-tertiary uppercase tracking-wide mb-3">
                Four gates — all must pass
              </p>
              <div className="space-y-2.5">
                {track.gates.map((gate) => (
                  <div key={gate.label}>
                    <span className="text-[13px] font-semibold text-text-primary flex items-start gap-2">
                      <span className="text-accent mt-0.5 flex-shrink-0">
                        &bull;
                      </span>
                      {gate.label}
                    </span>
                    <p className="text-[12px] text-text-tertiary leading-relaxed ml-4">
                      {gate.detail}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Conviction levels */}
        <motion.div
          className="flex flex-wrap gap-4 mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          {convictionLevels.map((cl) => (
            <div
              key={cl.level}
              className="px-4 py-3 border border-border-primary rounded-lg bg-bg-elevated"
            >
              <span className="text-[13px] font-semibold text-accent block mb-1 font-mono">
                {cl.level}
              </span>
              <span className="text-[12px] text-text-secondary">
                {cl.meaning}
              </span>
            </div>
          ))}
        </motion.div>

        {/* Candidate journey chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
          className="max-w-2xl"
        >
          <CandidateJourneyChart />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4 max-w-2xl"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.18, ease }}
        >
          As a company&apos;s fundamentals improve and the market hasn&apos;t
          repriced, the composite tier rises. The engine tracks this progression
          automatically.
        </motion.p>
      </div>
    </section>
  )
}
