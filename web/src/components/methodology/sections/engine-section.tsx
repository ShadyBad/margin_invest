"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const pipelineStages = [
  { label: "Universe", desc: "Selection" },
  { label: "Data", desc: "Normalization" },
  { label: "Filters", desc: "Elimination" },
  { label: "Factors", desc: "Analysis" },
  { label: "Score", desc: "Composite" },
  { label: "Conviction", desc: "Ranking" },
  { label: "Allocation", desc: "Guidance" },
]

const factors = [
  {
    name: "Quality",
    color: "text-accent",
    desc: "Measures operational strength and durability. Companies that generate high returns on capital, maintain healthy balance sheets, and produce consistent earnings rank highest.",
    metrics: ["Return on equity", "Debt-to-equity", "Earnings consistency", "Profit margins"],
  },
  {
    name: "Value",
    color: "text-accent",
    desc: "Identifies companies trading below estimated intrinsic value. Compares price multiples against sector peers and historical norms to find mispricing opportunities.",
    metrics: ["Price-to-earnings", "Price-to-book", "Free cash flow yield", "Margin of safety"],
  },
  {
    name: "Momentum",
    color: "text-accent",
    desc: "Captures sustained directional price movement and trend persistence. Equities with strong relative strength across multiple timeframes score higher.",
    metrics: ["Relative strength", "Trend persistence", "Price acceleration", "Volume confirmation"],
  },
]

function PipelineArrow() {
  return (
    <svg width="20" height="12" viewBox="0 0 20 12" fill="none" className="text-border-primary flex-shrink-0 hidden sm:block">
      <line x1="0" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth="1" />
      <path d="M12 2 L18 6 L12 10" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  )
}

export function EngineSection() {
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
          The Engine
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          From raw data to conviction.
        </motion.h2>

        {/* Pipeline Flow Diagram */}
        <motion.div
          className="mb-16 p-6 border border-border-primary rounded-lg bg-bg-elevated overflow-x-auto"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          {/* Desktop/Tablet: horizontal flow */}
          <div className="hidden sm:flex items-center justify-between gap-2">
            {pipelineStages.map((stage, i) => (
              <div key={stage.label} className="flex items-center gap-2">
                <div className="flex flex-col items-center text-center min-w-[80px]">
                  <span className="text-[11px] font-mono font-bold text-accent">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-[13px] font-semibold text-text-primary mt-1">
                    {stage.label}
                  </span>
                  <span className="text-[11px] text-text-tertiary mt-0.5">
                    {stage.desc}
                  </span>
                </div>
                {i < pipelineStages.length - 1 && <PipelineArrow />}
              </div>
            ))}
          </div>

          {/* Mobile: vertical flow */}
          <div className="flex flex-col gap-3 sm:hidden">
            {pipelineStages.map((stage, i) => (
              <div key={stage.label} className="flex items-center gap-3">
                <span className="text-[11px] font-mono font-bold text-accent w-5 flex-shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="text-[13px] font-semibold text-text-primary">
                  {stage.label}
                </span>
                <span className="text-[11px] text-text-tertiary">
                  {stage.desc}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Factor Pillars */}
        <motion.h3
          className="text-[20px] font-semibold text-text-primary mb-8"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Three pillars of evaluation
        </motion.h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {factors.map((factor, i) => (
            <motion.div
              key={factor.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h4 className={`text-[18px] font-semibold ${factor.color} mb-3`}>
                {factor.name}
              </h4>
              <p className="text-[14px] text-text-secondary leading-relaxed mb-4">
                {factor.desc}
              </p>
              <div className="space-y-1">
                {factor.metrics.map((metric) => (
                  <span
                    key={metric}
                    className="block text-[12px] text-text-tertiary font-mono"
                  >
                    {metric}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Conviction & Risk */}
        <motion.div
          className="max-w-2xl space-y-4 text-[14px] sm:text-[15px] text-text-secondary leading-relaxed"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p>
            <span className="text-text-primary font-medium">Conviction</span> is not a
            prediction — it&apos;s a measure of factor alignment. When quality, value, and momentum
            converge for a given equity, conviction rises. When they diverge, it falls. The score
            reflects how many independent signals agree, not how much the price will move.
          </p>
          <p>
            <span className="text-text-primary font-medium">Risk</span> is embedded at every
            stage. Elimination filters remove equities with disqualifying characteristics before
            scoring begins. Volatility, drawdown history, and margin of safety are factored into
            both the conviction score and the allocation guidance.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
