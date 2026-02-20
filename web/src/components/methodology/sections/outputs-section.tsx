"use client"

import { motion } from "framer-motion"
import { MarginOfSafetyBand } from "../visuals/margin-of-safety-band"

const ease = [0.22, 1, 0.36, 1] as const

const outputs = [
  {
    title: "Candidate cards",
    desc: "Each stock on your dashboard shows its conviction level, opportunity type (Compounder or Mispricing), signal (Buy / Hold / Sell), and pillar percentile bars \u2014 all at a glance. Click any card to open the full analysis.",
  },
  {
    title: "Factor breakdown",
    desc: "Drill into the exact Quality, Value, and Momentum percentile scores. See which factors are driving the conviction level and which are holding it back. Every score is auditable \u2014 no black boxes.",
  },
  {
    title: "Price target framework",
    desc: "The engine synthesizes multiple valuation methods into a single Margin Invest Value, then applies a dynamic margin of safety to produce a buy price and a sell price. You always know where the current price sits relative to the engine\u2019s assessment.",
  },
  {
    title: "Position sizing",
    desc: "Suggested allocation percentages are tied directly to conviction strength and opportunity type. Higher conviction and stronger factor alignment earn a larger suggested position. The engine does the sizing math so you don\u2019t have to.",
  },
]

export function OutputsSection() {
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
          Product Outputs
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Structured outputs you can act on — not opinions to interpret.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Every scored candidate produces a set of concrete outputs designed to
          eliminate ambiguity. You see exactly why a stock scores the way it does,
          what price represents a good entry, and how much of your portfolio it warrants.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {outputs.map((output, i) => (
            <motion.div
              key={output.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {output.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {output.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Margin of Safety Band */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <MarginOfSafetyBand />
        </motion.div>

        <motion.p
          className="text-[14px] text-text-secondary leading-relaxed mt-6 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15, ease }}
        >
          When the current price falls below the buy price, the signal is Buy.
          Between buy and sell, it&apos;s Hold. Above the sell target, it&apos;s Sell.
          The margin of safety widens or tightens based on how much the valuation
          methods agree.
        </motion.p>
      </div>
    </section>
  )
}
