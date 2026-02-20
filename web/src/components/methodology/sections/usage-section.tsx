"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const doItems = [
  "Use candidates as a starting point for your own research",
  "Review the factor breakdown to understand why a stock scores well",
  "Compare the engine\u2019s price target to your own valuation work",
  "Use position sizing as a framework, then adjust for your risk tolerance",
  "Monitor conviction changes over time \u2014 a rising score often confirms an improving fundamental picture",
]

const dontItems = [
  "Don\u2019t treat a high conviction score as a buy recommendation",
  "Don\u2019t skip your own due diligence because the engine did quantitative work",
  "Don\u2019t ignore the limitations section below",
  "Don\u2019t assume past scoring accuracy predicts future results",
]

export function UsageSection() {
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
          Responsible Usage
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          What to do — and not do — with these candidates.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Margin Invest surfaces candidates and quantifies conviction. It does not
          make decisions for you. Here&apos;s how to get the most value from the output.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {/* Do list */}
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease }}
          >
            <ul className="space-y-3">
              {doItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
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
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Don't list */}
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.18, ease }}
          >
            <ul className="space-y-3">
              {dontItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    className="text-bearish flex-shrink-0 mt-0.5"
                  >
                    <path
                      d="M4 4L12 12M12 4L4 12"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          The engine replaces the tedious parts of investment analysis — data gathering,
          normalization, cross-factor comparison, and ranking. The judgment call on
          whether to act is always yours.
        </motion.p>
      </div>
    </section>
  )
}
