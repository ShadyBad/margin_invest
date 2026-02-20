"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const outcomes = [
  "Scores updated daily after market close",
  "Transparent factor breakdowns you can audit",
  "Quantified conviction levels, not subjective ratings",
  "Price targets with explicit margin of safety",
  "Position sizing tied to conviction strength",
]

const builtFor = [
  "Self-directed investors who want a repeatable process",
  "Portfolio managers who value transparency over tips",
  "Analysts who want to eliminate blind spots",
]

const notFor = [
  "Traders looking for intraday signals",
  "Anyone expecting guaranteed returns",
  "Passive index investors",
]

export function HeroSection() {
  return (
    <section>
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
          How It Works
        </motion.p>

        <motion.h1
          className="heading-1 text-text-primary mb-6 max-w-3xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          From 7,000+ stocks to the ones worth your attention.
        </motion.h1>

        <motion.p
          className="text-[16px] sm:text-[17px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Margin Invest runs every US-listed equity through a deterministic pipeline of
          elimination filters, multi-factor scoring, and conviction ranking — daily.
          Same inputs, same outputs. No human judgment anywhere in the process.
        </motion.p>

        {/* Outcome bullets */}
        <motion.ul
          className="space-y-3 mb-14"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          {outcomes.map((item) => (
            <li key={item} className="flex items-start gap-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="text-accent flex-shrink-0 mt-0.5"
              >
                <path
                  d="M3 8.5L6.5 12L13 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-[14px] sm:text-[15px] text-text-primary">
                {item}
              </span>
            </li>
          ))}
        </motion.ul>

        {/* Who it's for / not for */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              Built for
            </h3>
            <ul className="space-y-2">
              {builtFor.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-accent text-[14px] leading-relaxed">+</span>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.28, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              Not built for
            </h3>
            <ul className="space-y-2">
              {notFor.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-text-tertiary text-[14px] leading-relaxed">–</span>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
