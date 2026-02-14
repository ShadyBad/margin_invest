"use client"

import { motion } from "framer-motion"

const metrics = [
  { label: "Excess CAGR", value: "\u2014", description: "vs S&P 500 (backtest pending)" },
  { label: "Sharpe Ratio", value: "\u2014", description: "Risk-adjusted returns" },
  { label: "Max Drawdown", value: "\u2014", description: "Worst peak-to-trough" },
  { label: "Win Rate", value: "\u2014", description: "Stocks beating benchmark" },
]

export function Performance() {
  return (
    <section className="py-24 px-4 bg-bg-elevated">
      <div className="max-w-5xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl font-bold text-text-primary mb-4 text-center"
        >
          Performance
        </motion.h2>
        <p className="text-text-secondary text-center mb-16">
          Walk-forward backtest results from Jan 2015 to present
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {metrics.map((metric, i) => (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-accent mb-2">{metric.value}</div>
              <div className="text-text-primary font-medium">{metric.label}</div>
              <div className="text-sm text-text-secondary mt-1">{metric.description}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
