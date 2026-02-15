"use client"

import { motion } from "framer-motion"
import { CapabilityBlock } from "../capability-block"

const ease = [0.22, 1, 0.36, 1] as const

const capabilities = [
  {
    title: "Structured Allocation",
    description:
      "Systematic position sizing derived from composite scores, removing discretionary drift from portfolio construction.",
    tinted: false,
    className: "col-span-4 md:col-span-8 lg:col-span-5",
    marginTop: "",
  },
  {
    title: "Quantified Risk",
    description:
      "Every position carries a deterministic risk profile — drawdown potential, volatility rank, and sector exposure measured precisely.",
    tinted: true,
    className: "col-span-4 md:col-span-8 lg:col-start-7 lg:col-span-6",
    marginTop: "lg:mt-[48px]",
  },
  {
    title: "Scenario Modeling",
    description:
      "Stress-test allocations against historical regimes and hypothetical shocks before committing capital.",
    tinted: false,
    className: "col-span-4 md:col-span-8 lg:col-start-2 lg:col-span-6",
    marginTop: "lg:mt-[32px]",
  },
  {
    title: "Bias Reduction",
    description:
      "Eliminate recency bias, anchoring, and narrative attachment. The engine scores what the data shows, not what you hope.",
    tinted: true,
    className: "col-span-4 md:col-span-8 lg:col-start-8 lg:col-span-5",
    marginTop: "lg:mt-[64px]",
  },
]

export function CapabilitiesSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "120px",
          paddingBottom: "120px",
        }}
      >
        {capabilities.map((cap, i) => (
          <motion.div
            key={cap.title}
            className={`${cap.className} ${cap.marginTop}`}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.1, ease }}
          >
            <CapabilityBlock
              title={cap.title}
              description={cap.description}
              tinted={cap.tinted}
            />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
