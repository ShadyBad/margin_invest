"use client"

import { motion } from "framer-motion"
import { CandidateJourneyChart } from "../visuals/candidate-journey-chart"

const ease = [0.22, 1, 0.36, 1] as const

const tracks = [
  {
    name: "Track A \u2014 Compounder",
    desc: "Identifies businesses with durable competitive advantages and strong reinvestment engines. These are companies where incremental capital deployed earns high returns \u2014 the kind of business that compounds value over long holding periods.",
    signals: [
      "Evidence of an economic moat (multiple structural signals)",
      "A reinvestment engine that converts retained earnings into growth",
      "Disciplined capital allocation",
      "A valuation that doesn\u2019t already price in perfection",
    ],
  },
  {
    name: "Track B \u2014 Mispricing",
    desc: "Identifies stocks trading at a significant discount to intrinsic value with a catalyst to close the gap. These are situations where multiple valuation methods converge on a higher value than the market price, and smart money is starting to notice.",
    signals: [
      "Multiple valuation methods agreeing the stock is cheap",
      "Downside protection (a floor on how much you can lose)",
      "A catalyst \u2014 insider buying, institutional accumulation, or earnings momentum",
      "A minimum quality floor (cheap for a reason doesn\u2019t qualify)",
    ],
  },
]

const convictionLevels = [
  {
    level: "Exceptional",
    meaning: "Strongest factor alignment across the universe",
  },
  {
    level: "High",
    meaning: "Strong multi-factor case with clear margin of safety",
  },
  {
    level: "Watchlist",
    meaning: "Promising but missing one dimension",
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
          Conviction System
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Two independent lenses. One conviction score.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Not every great investment looks the same. Some are durable compounders you
          want to hold for years. Others are deeply mispriced assets where the market
          hasn&apos;t caught up to the fundamentals. The engine runs both analyses in
          parallel — a stock can qualify through either track, or both.
        </motion.p>

        {/* Track cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {tracks.map((track, i) => (
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
              <p className="text-[12px] font-medium text-text-tertiary uppercase tracking-wide mb-2">
                What the engine looks for
              </p>
              <ul className="space-y-1.5">
                {track.signals.map((signal) => (
                  <li
                    key={signal}
                    className="text-[13px] text-text-secondary leading-relaxed flex items-start gap-2"
                  >
                    <span className="text-accent mt-0.5 flex-shrink-0">&bull;</span>
                    {signal}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Orchestration note */}
        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          When a stock qualifies on both tracks simultaneously — a high-quality
          compounder that also happens to be mispriced — it receives the highest
          conviction level and the largest suggested position size.
        </motion.p>

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
              <span className="text-[13px] font-semibold text-accent block mb-1">
                {cl.level}
              </span>
              <span className="text-[12px] text-text-secondary">{cl.meaning}</span>
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
          As a company&apos;s fundamentals improve and the market hasn&apos;t repriced,
          conviction rises. The engine tracks this progression automatically.
        </motion.p>
      </div>
    </section>
  )
}
