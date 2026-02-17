"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const stages = [
  {
    label: "Market Data",
    desc: "Real-time price feeds, fundamentals, and financial statements from institutional-grade sources.",
  },
  {
    label: "Elimination Filters",
    desc: "Fail-fast binary checks remove disqualified equities before any scoring begins.",
  },
  {
    label: "Factor Scoring",
    desc: "Percentile-ranked scoring across value, momentum, quality, growth, and stability factors.",
  },
  {
    label: "Composite Output",
    desc: "Weighted factor synthesis produces a single conviction score with full factor breakdown.",
  },
]

function StageIcon({ index }: { index: number }) {
  return (
    <div className="w-10 h-10 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0 bg-bg-elevated">
      <span className="text-[14px] font-bold text-accent font-mono">
        {String(index + 1).padStart(2, "0")}
      </span>
    </div>
  )
}

function Arrow() {
  return (
    <div className="hidden lg:flex items-center justify-center flex-shrink-0 w-8">
      <svg width="32" height="12" viewBox="0 0 32 12" fill="none" className="text-border-primary">
        <line x1="0" y1="6" x2="24" y2="6" stroke="currentColor" strokeWidth="1" />
        <path d="M22 2 L30 6 L22 10" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
    </div>
  )
}

export function PipelineSection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-12"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          The Pipeline
        </motion.p>

        {/* Desktop: horizontal */}
        <div className="hidden lg:flex items-start justify-between">
          {stages.map((stage, i) => (
            <div key={stage.label} className="flex items-start">
              <motion.div
                className="flex flex-col items-center text-center max-w-[220px]"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1, ease }}
              >
                <StageIcon index={i} />
                <span className="text-[15px] font-semibold text-text-primary mt-3">
                  {stage.label}
                </span>
                <span className="text-[13px] text-text-secondary mt-2 leading-relaxed">
                  {stage.desc}
                </span>
              </motion.div>
              {i < stages.length - 1 && <Arrow />}
            </div>
          ))}
        </div>

        {/* Tablet: 2x2 grid */}
        <div className="hidden md:grid md:grid-cols-2 gap-4 lg:hidden">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.label}
              className="flex items-start gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <StageIcon index={i} />
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {stage.label}
                </span>
                <span className="text-[12px] text-text-secondary mt-1 block leading-relaxed">
                  {stage.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical stack */}
        <div className="flex flex-col gap-3 md:hidden">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.label}
              className="flex items-start gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <StageIcon index={i} />
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {stage.label}
                </span>
                <span className="text-[12px] text-text-secondary mt-1 block leading-relaxed">
                  {stage.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
