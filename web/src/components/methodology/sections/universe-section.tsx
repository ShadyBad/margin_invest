"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const cards = [
  {
    title: "What\u2019s included",
    items: [
      "~7,000+ US-domiciled equities",
      "9 sectors: Technology, Healthcare, Industrials, Energy, Consumer Cyclical, Consumer Defensive, Basic Materials, Utilities, Communication Services",
      "All market caps above liquidity minimums",
    ],
  },
  {
    title: "What\u2019s excluded",
    items: [
      "Financials \u2014 leverage-as-product breaks ROIC metrics",
      "Real Estate \u2014 REITs use different valuation frameworks",
      "OTC / Pink Sheet listings",
      "Foreign ADRs",
    ],
  },
  {
    title: "Data freshness",
    items: [
      "Full scoring cycle runs daily after market close (4:30 PM ET)",
      "Scores refresh within ~2 hours of the closing bell",
      "Each score carries a freshness label: Fresh, Stale, or Expired",
    ],
  },
]

export function UniverseSection() {
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
          Universe Selection
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Every US-listed equity. No cherry-picking.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          The engine starts with the full universe of US-listed equities across all
          major exchanges — NYSE, NASDAQ, and NYSE American. Financials and Real Estate
          are excluded because their capital structures make standard profitability
          metrics unreliable. Everything else is in.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-4">
                {card.title}
              </h3>
              <ul className="space-y-2">
                {card.items.map((item) => (
                  <li
                    key={item}
                    className="text-[13px] text-text-secondary leading-relaxed"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
