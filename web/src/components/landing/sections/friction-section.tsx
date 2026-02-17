"use client"

import { motion } from "framer-motion"
import { ConstellationNarrative } from "./constellation-narrative"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

export function FrictionSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1200px",
          paddingLeft: "10vw",
          paddingRight: "10vw",
          paddingTop: "120px",
          paddingBottom: "140px",
        }}
      >
        <div className="col-span-4 md:col-span-4 lg:col-span-6 flex flex-col gap-6">
          {lines.map((line, i) => (
            <motion.h3
              key={line}
              className="font-display text-[32px] md:text-[36px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]"
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.2, ease }}
            >
              {line}
            </motion.h3>
          ))}
          <motion.p
            className="text-[15px] text-text-secondary leading-relaxed max-w-[480px]"
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6, ease }}
          >
            Behavioral finance research shows that emotional trading costs retail investors
            1.5–4% annually. Structure eliminates the leak.*
          </motion.p>
          <motion.span
            className="text-[11px] text-text-tertiary font-mono"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: 0.8 }}
          >
            * Barber & Odean, 2000; Dalbar QAIB, 2023
          </motion.span>
        </div>

        {/* Abstract market noise visualization — tablet + desktop */}
        <div className="hidden md:block md:col-start-5 md:col-span-4 lg:col-start-8 lg:col-span-5">
          <ConstellationNarrative />
        </div>
      </div>
    </section>
  )
}
