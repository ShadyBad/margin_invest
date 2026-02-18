"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    title: "Not financial advice",
    desc: "Margin Invest provides analytical tools and scoring frameworks for informational purposes. It does not provide personalized investment recommendations. You make the decisions.",
  },
  {
    title: "Model risk exists",
    desc: "All quantitative models have limitations. Historical data may not predict future performance. Factor correlations change. Data sources have gaps. No scoring system is infallible.",
  },
  {
    title: "Structure, not prediction",
    desc: "The engine helps you evaluate opportunities systematically. It does not predict which stocks will go up. It identifies where multiple quality signals align and quantifies the opportunity.",
  },
]

export function TrustSection() {
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
          What this is — and isn&apos;t.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
      </div>
    </section>
  )
}
