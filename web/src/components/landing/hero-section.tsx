"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { GridOverlay } from "./grid-overlay"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative" style={{ minHeight: "90vh" }}>
      <GridOverlay opacity={0.03} />
      <div
        className="relative mx-auto grid grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          padding: "160px 24px",
        }}
      >
        {/* Content: cols 1-8 */}
        <div className="col-span-12 md:col-span-8 flex flex-col justify-center">
          {/* Thin decorative rule */}
          <motion.div
            className="w-48 h-px bg-border-primary mb-12"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.7, ease }}
            style={{ transformOrigin: "left" }}
          />

          <motion.h1
            className="text-[40px] md:text-[52px] lg:text-[68px] font-bold leading-[0.98] tracking-[-0.03em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease }}
          >
            Structure outperforms emotion.
          </motion.h1>

          <motion.p
            className="mt-6 text-lg md:text-xl text-text-secondary max-w-[640px] leading-relaxed"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            A deterministic scoring engine that evaluates every US equity through
            the same institutional-grade framework — no discretion, no narrative
            bias, no exceptions.
          </motion.p>

          <motion.div
            className="mt-10 flex items-center gap-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-block px-8 py-4 bg-accent text-white font-semibold text-[15px] rounded-sm hover:bg-accent-hover transition-colors"
            >
              Explore the Engine
            </Link>
            <Link
              href="/methodology"
              className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              View methodology
            </Link>
          </motion.div>
        </div>

        {/* Cols 9-12: intentional negative space */}
      </div>
    </section>
  )
}
