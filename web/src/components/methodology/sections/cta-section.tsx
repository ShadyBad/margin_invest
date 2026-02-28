"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function CTASection() {
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
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p className="text-[16px] sm:text-[17px] text-text-secondary mb-8 max-w-lg mx-auto">
            See the full pipeline in action. Score any stock and get the
            complete factor breakdown, composite tier, and position sizing.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-12 px-8 text-[14px] font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
            >
              Explore the Dashboard
            </Link>
            <Link
              href="/guides"
              className="inline-flex items-center justify-center h-12 px-6 text-[14px] font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
            >
              Read the Guides
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
