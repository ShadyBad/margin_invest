"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const outputs = [
  {
    title: "Candidate cards",
    desc: "Each scored equity appears as a card showing its conviction score, signal, sector, and factor breakdown at a glance.",
  },
  {
    title: "Factor breakdown",
    desc: "Quality, value, and momentum percentiles shown as individual bars. See exactly which factors are driving the score up or down.",
  },
  {
    title: "Price target framework",
    desc: "Margin Invest Value estimate, buy-below price, sell target, and margin of safety — the key inputs for position entry and exit decisions.",
  },
  {
    title: "Allocation guidance",
    desc: "Suggested position sizing based on conviction strength and risk calibration. Timing signals indicate when factor alignment is strongest.",
  },
]

// Margin of Safety Band Chart — pure CSS/SVG
function MarginOfSafetyChart() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-6">
        Price vs. Margin Invest Value
      </p>

      <div className="relative h-24 mb-4">
        {/* Background band zones */}
        <div className="absolute inset-y-0 left-0 right-0 flex">
          <div className="flex-[25] bg-bullish/8 rounded-l-md" />
          <div className="flex-[20] bg-accent/5" />
          <div className="flex-[30] bg-warning/5" />
          <div className="flex-[25] bg-bearish/8 rounded-r-md" />
        </div>

        {/* Labels */}
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-[11px] font-medium text-bullish">Discount</span>
          </div>
          <div className="flex-[20] flex items-center justify-center">
            <span className="text-[11px] font-medium text-accent">Buy Below</span>
          </div>
          <div className="flex-[30] flex items-center justify-center">
            <span className="text-[11px] font-medium text-text-tertiary">Fair Value</span>
          </div>
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-[11px] font-medium text-bearish">Overvalued</span>
          </div>
        </div>

        {/* Price markers */}
        <div className="absolute bottom-0 left-0 right-0 flex text-[10px] font-mono text-text-tertiary">
          <div className="flex-[25] text-center">$120</div>
          <div className="flex-[20] text-center">$145</div>
          <div className="flex-[30] text-center">$175</div>
          <div className="flex-[25] text-center">$210</div>
        </div>

        {/* Marker lines */}
        <div className="absolute inset-y-2 left-[25%] w-px bg-border-primary" />
        <div className="absolute inset-y-2 left-[45%] w-px bg-accent/30" />
        <div className="absolute inset-y-2 left-[75%] w-px bg-border-primary" />
      </div>

      <div className="flex justify-between text-[11px] text-text-tertiary mt-2">
        <span>Buy Below</span>
        <span>Current Price</span>
        <span>Margin Invest Value</span>
        <span>Sell Target</span>
      </div>
    </div>
  )
}

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
          What You Get
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Structured outputs, not opinions.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
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

        {/* Margin of Safety Band Chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <MarginOfSafetyChart />
        </motion.div>

        <motion.p
          className="text-[14px] text-text-secondary leading-relaxed mt-6 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15, ease }}
        >
          The margin of safety framework shows where the current price sits relative to the
          estimated Margin Invest Value. When the price is in the discount zone, the risk/reward
          is most favorable. This is not a prediction — it&apos;s a structured way to evaluate entry
          and exit points.
        </motion.p>
      </div>
    </section>
  )
}
