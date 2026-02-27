"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const keyPoints = [
  {
    title: "13F filings",
    detail:
      "Institutional managers with $100M+ AUM are required to disclose equity holdings quarterly via SEC 13F filings. The system ingests these filings to track what institutional investors are doing with every stock in the universe.",
  },
  {
    title: "Accumulation signals",
    detail:
      "Changes in institutional positioning feed into the catalyst strength score within the Momentum pillar. When multiple high-conviction managers are accumulating a position, that signal strengthens the overall catalyst assessment.",
  },
  {
    title: "Curated manager list",
    detail:
      "Not all institutional managers are equal. The system maintains a curated list of high-conviction investors — managers with concentrated portfolios and strong long-term track records — and weights their activity more heavily.",
  },
  {
    title: "45-day reporting lag",
    detail:
      "13F filings are due 45 days after quarter-end. Positions may have changed since the filing date. The system accounts for this lag — institutional signals are one input among many, never a standalone signal.",
  },
]

export function SmartMoneySection() {
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
          Stage 6 · Smart Money Overlay
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          What institutional investors are doing with AAPL.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Finally, the system checks what institutional investors are doing
          with AAPL. This isn&apos;t a standalone signal — it&apos;s one input
          among many that feeds into the broader scoring framework.
        </motion.p>

        {/* Key points */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {keyPoints.map((point, i) => (
            <motion.div
              key={point.title}
              className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {point.title}
              </h3>
              <p className="text-[13px] text-text-secondary leading-relaxed">
                {point.detail}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Caveat */}
        <motion.p
          className="text-[12px] text-text-tertiary max-w-2xl"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.1, ease }}
        >
          Institutional positioning is a confirmation signal, not a primary
          driver. The engine will never recommend a stock solely because
          institutions are buying it.
        </motion.p>
      </div>
    </section>
  )
}
