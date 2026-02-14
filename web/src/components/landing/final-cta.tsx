"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { GridOverlay } from "./grid-overlay"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section className="relative" style={{ minHeight: "60vh" }}>
      <GridOverlay opacity={0.02} />
      <div
        className="relative mx-auto grid grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          padding: "120px 24px 160px",
        }}
      >
        {/* Content: cols 1-6 */}
        <div className="col-span-12 md:col-span-6">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, delay: 0.2, ease }}
          >
            See what survives the filter.
          </motion.h2>

          <motion.p
            className="mt-6 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[640px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            Start with the full pipeline. Every factor, every elimination check, every percentile
            rank — visible and auditable.
          </motion.p>

          <motion.div
            className="mt-10"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.6, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-block px-8 py-4 bg-accent text-white font-semibold text-[15px] rounded-sm hover:bg-accent-hover transition-colors"
            >
              Explore the Engine
            </Link>
          </motion.div>

          <motion.div
            className="mt-4"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.75, ease }}
          >
            <Link
              href="/methodology"
              className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              Read the methodology &rarr;
            </Link>
          </motion.div>
        </div>

        {/* Cols 7-12: intentional negative space */}
      </div>
    </section>
  )
}
