"use client"

import { motion } from "framer-motion"
import { PipelineDiagram } from "../visuals/pipeline-diagram"

const ease = [0.22, 1, 0.36, 1] as const

const stages = [
  { num: "1", label: "Universe", detail: "7,000+ stocks" },
  { num: "2", label: "Elimination Filters", detail: "6 pass/fail checks" },
  { num: "3", label: "Factor Scoring", detail: "Quality \u00b7 Value \u00b7 Momentum" },
  {
    num: "4",
    label: "Dual-Track Scoring",
    detail: "Compounder & Mispricing",
  },
  { num: "5", label: "ML Refinement", detail: "Cluster models, VAE" },
  {
    num: "6",
    label: "Smart Money Overlay",
    detail: "13F institutional signals",
  },
  {
    num: "7",
    label: "Position Sizing",
    detail: "Composite tier \u00d7 opportunity type",
  },
]

export function PipelineSection() {
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
          The Pipeline
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Seven stages. One stock at a time.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Let&apos;s follow Apple (AAPL) through the pipeline. At every stage,
          we&apos;ll show you exactly what the system checks and what it finds.
        </motion.p>

        {/* 7-stage list */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          {stages.map((stage) => (
            <div
              key={stage.num}
              className="p-4 border border-border-primary rounded-lg bg-bg-elevated"
            >
              <span className="text-[11px] font-mono font-bold text-accent">
                {stage.num}
              </span>
              <h3 className="text-[13px] font-semibold text-text-primary mt-1">
                {stage.label}
              </h3>
              <p className="text-[11px] text-text-tertiary mt-0.5">
                {stage.detail}
              </p>
            </div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.24, ease }}
        >
          <PipelineDiagram />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.32, ease }}
        >
          The pipeline runs automatically after each market close. Scores
          typically refresh within 2 hours of the closing bell.
        </motion.p>
      </div>
    </section>
  )
}
