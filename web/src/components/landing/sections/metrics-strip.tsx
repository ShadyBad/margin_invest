"use client"

import { motion } from "framer-motion"

const metrics = [
  { number: "2,400+", label: "equities scored daily" },
  { number: "6", label: "quantitative factors" },
  { label: "Updated every market close" },
]

export function MetricsStrip() {
  return (
    <motion.div
      className="flex flex-wrap items-center justify-center gap-6 text-[13px] font-mono text-text-tertiary tracking-[0.3px] py-4"
      style={{ maxWidth: "1200px", margin: "0 auto", paddingLeft: "10vw", paddingRight: "10vw" }}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {metrics.map((m, i) => (
        <span key={m.label} className="flex items-center gap-6">
          {i > 0 && <span className="text-border-primary">|</span>}
          <span>
            {m.number && <span className="font-display text-[15px]">{m.number} </span>}
            {m.label}
          </span>
        </span>
      ))}
    </motion.div>
  )
}
