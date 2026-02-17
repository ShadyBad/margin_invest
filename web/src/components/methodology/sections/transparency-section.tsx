"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    label: "Deterministic",
    detail: "Same inputs always produce the same outputs. No randomness, no discretion.",
  },
  {
    label: "Sector-Neutral",
    detail: "Equities are ranked within their GICS sector before cross-sector comparison.",
  },
  {
    label: "Transparent",
    detail: "Every score includes a full factor breakdown. No black boxes.",
  },
]

export function TransparencySection() {
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
        <motion.div
          className="text-center max-w-[640px] mx-auto mb-12"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4">
            Principles
          </p>
          <h2 className="text-[32px] md:text-[40px] font-bold text-text-primary leading-tight tracking-[-0.3px]">
            Structure you can verify.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-[960px] mx-auto">
          {principles.map((p, i) => (
            <motion.div
              key={p.label}
              className="p-6 border border-border-primary rounded-[6px] bg-bg-elevated text-center"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <h3 className="text-[18px] font-semibold text-text-primary mb-2">
                {p.label}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {p.detail}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
