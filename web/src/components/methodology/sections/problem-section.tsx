"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const problems = [
  {
    title: "Noisy markets",
    desc: "Thousands of stocks, endless headlines, and conflicting analyst opinions. The signal-to-noise ratio in public markets makes consistent analysis nearly impossible without structure.",
  },
  {
    title: "Information overload",
    desc: "Financial data is abundant but unstructured. Earnings reports, price action, macro trends, and sector dynamics create a firehose that resists manual synthesis.",
  },
  {
    title: "Emotional decision-making",
    desc: "Fear and greed drive most retail portfolios. Without a repeatable framework, conviction erodes at exactly the moments it matters most.",
  },
  {
    title: "No repeatable process",
    desc: "Most investors lack a consistent method for evaluating, comparing, and sizing positions. Every decision starts from scratch.",
  },
]

export function ProblemSection() {
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
          The Problem
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Most investment research creates noise, not clarity.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {problems.map((problem, i) => (
            <motion.div
              key={problem.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {problem.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {problem.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
