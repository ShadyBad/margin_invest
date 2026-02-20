"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    title: "Not financial advice",
    desc: "Margin Invest is an analytical tool for informational and educational purposes. Conviction scores, price targets, and position sizing suggestions are model outputs \u2014 not recommendations to buy, sell, or hold any security. You make the decisions.",
  },
  {
    title: "Models have limits",
    desc: "The engine relies on publicly available financial data. Data can be delayed, restated, or incomplete. Quantitative models cannot capture qualitative factors like management quality, regulatory changes, or geopolitical risk. Edge cases exist in every model.",
  },
  {
    title: "Structure, not prediction",
    desc: "The engine identifies where quality, value, and momentum signals align. It does not predict future prices. A high conviction score means strong current factor alignment \u2014 not a guarantee that the stock will outperform.",
  },
]

const checklist = [
  "Does the thesis make sense to you independent of the score?",
  "Have you checked for recent news the model can\u2019t capture (M&A, litigation, regulatory)?",
  "Is the position size appropriate for your portfolio and risk tolerance?",
  "Do you have an exit plan \u2014 not just an entry plan?",
  "Are you comfortable holding through a drawdown if the fundamentals haven\u2019t changed?",
]

export function TransparencySection() {
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
          Transparency
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          What this is — and what it isn&apos;t.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {principles.map((principle, i) => (
            <motion.div
              key={principle.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                {principle.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {principle.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Validation checklist */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h3 className="text-[17px] font-semibold text-text-primary mb-6">
            Before acting on any candidate, verify:
          </h3>
          <ul className="space-y-3 max-w-2xl">
            {checklist.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <div className="w-4 h-4 rounded border border-border-primary flex-shrink-0 mt-0.5" />
                <span className="text-[14px] text-text-secondary leading-relaxed">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
      </div>
    </section>
  )
}
