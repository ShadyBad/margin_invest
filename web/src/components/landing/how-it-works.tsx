"use client"

import { motion } from "framer-motion"

const steps = [
  {
    number: "01",
    title: "Elimination Filters",
    description: "Screen out low-quality, illiquid, and ineligible stocks. Only survivors advance.",
  },
  {
    number: "02",
    title: "Quantitative Scoring",
    description: "Score on quality, value, and momentum using battle-tested academic factors.",
  },
  {
    number: "03",
    title: "Conviction Rating",
    description: "Combine factor scores into a single percentile rank. Top 5% earn conviction.",
  },
  {
    number: "04",
    title: "Continuous Monitoring",
    description: "Real-time events trigger re-scoring. Signals update automatically.",
  },
]

export function HowItWorks() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl font-bold text-text-primary mb-16 text-center"
        >
          How It Works
        </motion.h2>
        <div className="grid md:grid-cols-2 gap-8">
          {steps.map((step, i) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="bg-bg-secondary border border-border rounded-xl p-8"
            >
              <span className="text-gold font-mono text-sm">{step.number}</span>
              <h3 className="text-xl font-bold text-text-primary mt-2 mb-3">{step.title}</h3>
              <p className="text-text-secondary">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
