"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const problems = [
  "No filtering discipline",
  "No factor weighting memory",
  "No sector normalization",
  "No portfolio-level correlation awareness",
]

export function ProblemSection() {
  return (
    <section id="problem" className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-10"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Most investors react. Few operate with structure.
        </motion.h2>

        <ul className="space-y-4 mb-10">
          {problems.map((problem, i) => (
            <motion.li
              key={problem}
              className="text-lg text-text-secondary flex items-start gap-3"
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1, ease }}
            >
              <span className="text-text-tertiary mt-1">—</span>
              {problem}
            </motion.li>
          ))}
        </ul>

        <motion.p
          className="text-lg text-text-primary font-medium"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
        >
          Margin Invest replaces guesswork with a repeatable system.
        </motion.p>

        <div className="mt-16 border-b border-border-subtle" />
      </div>
    </section>
  )
}
