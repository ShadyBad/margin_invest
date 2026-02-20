"use client"

import { motion } from "framer-motion"
import { PipelineDiagram } from "../visuals/pipeline-diagram"

const ease = [0.22, 1, 0.36, 1] as const

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
          From raw data to conviction — every day.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Each scoring cycle runs the same sequence. Every stage is deterministic:
          same data in, same scores out.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          <PipelineDiagram />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.24, ease }}
        >
          The pipeline runs automatically after each market close. Scores typically
          refresh within 2 hours of the closing bell.
        </motion.p>
      </div>
    </section>
  )
}
