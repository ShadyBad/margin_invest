"use client"

import { motion } from "framer-motion"
import { MarginOfSafetyBand } from "../visuals/margin-of-safety-band"

const ease = [0.22, 1, 0.36, 1] as const

const exampleOutput = [
  { label: "Conviction", value: "HIGH", color: "text-accent" },
  { label: "Opportunity Type", value: "Compounder", color: "text-text-primary" },
  { label: "Suggested Position", value: "8%", color: "text-text-primary" },
]

const factorBreakdown = [
  { pillar: "Quality", percentile: 82, suffix: "nd", color: "text-accent" },
  { pillar: "Value", percentile: 64, suffix: "th", color: "text-bullish" },
  { pillar: "Momentum", percentile: 71, suffix: "st", color: "text-warning" },
]

const outputFields = [
  {
    title: "Conviction level",
    desc: "How strongly the factor evidence supports the investment case. Ranges from NONE to EXCEPTIONAL based on gate alignment.",
  },
  {
    title: "Opportunity type",
    desc: "Whether the stock qualifies as a Compounder (durable advantage), Mispricing (discount to intrinsic value), or both.",
  },
  {
    title: "Suggested position size",
    desc: "An allocation percentage calibrated to conviction strength and opportunity type. Higher conviction earns a larger position.",
  },
  {
    title: "Factor breakdown",
    desc: "The individual Quality, Value, and Momentum percentile scores — so you see exactly which dimensions are driving the conviction level.",
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
          Stage 7 · Position Sizing
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          After all stages, AAPL receives its final output.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Seven stages of analysis produce a set of concrete, actionable
          outputs. No ambiguity — you see exactly why a stock scores the way
          it does, what conviction level it earns, and how much of your
          portfolio it warrants.
        </motion.p>

        {/* Example AAPL output */}
        <motion.div
          className="p-6 border border-border-primary rounded-lg bg-bg-elevated mb-6 max-w-lg"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p className="text-[12px] font-medium text-text-tertiary uppercase tracking-wide mb-4">
            Example output — AAPL
          </p>
          <div className="space-y-3 mb-4">
            {exampleOutput.map((item) => (
              <div key={item.label} className="flex items-baseline justify-between">
                <span className="text-[13px] text-text-secondary">
                  {item.label}
                </span>
                <span className={`text-[14px] font-mono font-semibold ${item.color}`}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t border-border-subtle pt-3">
            <p className="text-[12px] font-medium text-text-tertiary uppercase tracking-wide mb-2">
              Factor breakdown
            </p>
            <div className="space-y-2">
              {factorBreakdown.map((fb) => (
                <div key={fb.pillar} className="flex items-center gap-3">
                  <span className={`text-[13px] font-semibold ${fb.color} w-24`}>
                    {fb.pillar}
                  </span>
                  <div className="flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent/60 rounded-full"
                      style={{ width: `${fb.percentile}%` }}
                    />
                  </div>
                  <span className="text-[12px] font-mono text-text-tertiary w-10 text-right">
                    {fb.percentile}{fb.suffix}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Output field explanations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {outputFields.map((field, i) => (
            <motion.div
              key={field.title}
              className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {field.title}
              </h3>
              <p className="text-[13px] text-text-secondary leading-relaxed">
                {field.desc}
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
          Between buy and sell, it&apos;s Hold. Above the sell target,
          it&apos;s Sell. The margin of safety widens or tightens based on how
          much the valuation methods agree.
        </motion.p>
      </div>
    </section>
  )
}
