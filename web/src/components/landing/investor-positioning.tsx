"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section style={{ padding: "80px 24px" }}>
      <div
        className="mx-auto grid grid-cols-12"
        style={{ maxWidth: "1280px" }}
      >
        {/* Offset content to cols 2-8 for rhythm variation */}
        <div className="col-span-12 md:col-start-2 md:col-span-7">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            Discipline compounds.
          </motion.h2>

          <motion.p
            className="mt-6 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[640px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
          >
            The edge isn&apos;t a single insight — it&apos;s a system that applies the same rigor to every decision. Margin Invest doesn&apos;t replace your judgment. It ensures every position you take has passed the same institutional-grade threshold.
          </motion.p>

          {/* Emerald horizontal rule */}
          <motion.div
            className="mt-10 h-px bg-accent/30"
            style={{ width: "33%" }}
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.4, ease }}
          />

          {/* Data point */}
          <motion.div
            className="mt-10"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.6, ease }}
          >
            <span className="text-[40px] md:text-[56px] font-bold leading-none tracking-[-0.02em] text-text-primary">
              Top 1% → 5–10 positions
            </span>
            <div className="text-[17px] text-text-primary mt-1">per cycle.</div>
          </motion.div>

          <motion.p
            className="mt-4 text-[14px] text-text-tertiary"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.8, ease }}
          >
            Exceptional conviction. The narrowest filter in the pipeline.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
