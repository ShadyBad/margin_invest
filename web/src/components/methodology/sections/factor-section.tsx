"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const factors = [
  {
    title: "Value",
    description:
      "Price-to-earnings, price-to-book, and free cash flow yield compared against sector peers.",
  },
  {
    title: "Momentum",
    description:
      "Relative strength across multiple timeframes, measuring sustained directional price movement.",
  },
  {
    title: "Quality",
    description:
      "Return on equity, debt ratios, and earnings consistency — indicators of operational strength.",
  },
  {
    title: "Growth",
    description:
      "Revenue and earnings growth rates, adjusted for the company's growth stage and sector norms.",
  },
  {
    title: "Stability",
    description:
      "Volatility rank, drawdown history, and beta — measuring how predictably an equity behaves.",
  },
]

export function FactorSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "96px",
        }}
      >
        <motion.div
          className="col-span-4 md:col-span-8 lg:col-span-5 flex flex-col justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4">
            Scoring Factors
          </p>
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            Five factors. One score.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
            Each equity is scored across five orthogonal factors. Scores are
            percentile-ranked within GICS sector first, then combined into a
            single composite.
          </p>
        </motion.div>

        <div className="col-span-4 md:col-span-8 lg:col-start-7 lg:col-span-6 flex flex-col gap-3">
          {factors.map((factor, i) => (
            <motion.div
              key={factor.title}
              className="p-5 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-[11px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-[16px] font-semibold text-text-primary">
                  {factor.title}
                </h3>
              </div>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {factor.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
