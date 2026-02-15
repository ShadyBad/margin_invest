"use client"

import { motion } from "framer-motion"
import { DiagramNodeLabel } from "../diagram-node-label"

const ease = [0.22, 1, 0.36, 1] as const

const nodes = ["Market Data", "Risk Modeling", "Allocation Engine", "Decision Clarity"]

export function EngineDiagram() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "120px",
          paddingBottom: "120px",
        }}
      >
        {/* Desktop: 4-column horizontal layout */}
        <div className="hidden md:grid md:grid-cols-4 gap-6">
          {nodes.map((label, i) => (
            <motion.div
              key={label}
              className="flex flex-col items-center gap-3"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <div className="w-3 h-3 rounded-full bg-border-primary" />
              <DiagramNodeLabel label={label} active={false} />
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical stacked with dot indicators */}
        <div className="flex flex-col gap-6 md:hidden">
          {nodes.map((label, i) => (
            <motion.div
              key={label}
              className="flex items-center gap-4"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <div className="w-2.5 h-2.5 rounded-full bg-border-primary flex-shrink-0" />
              <DiagramNodeLabel label={label} active={false} />
            </motion.div>
          ))}
        </div>

        {/* Annotation */}
        <motion.p
          className="mt-12 text-[13px] text-text-secondary italic"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.5, ease }}
        >
          This section transitions into interactive WebGL stage.
        </motion.p>
      </div>
    </section>
  )
}
