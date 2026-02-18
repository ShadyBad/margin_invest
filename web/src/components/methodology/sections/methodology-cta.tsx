"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function MethodologyCTA() {
  return (
    <section className="border-t border-border-subtle">
      <div
        className="mx-auto text-center"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.h2
          className="heading-2 text-text-primary mb-4"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Start building a disciplined watchlist.
        </motion.h2>

        <motion.p
          className="text-[16px] sm:text-[17px] text-text-secondary mb-8 max-w-lg mx-auto"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Run any equity through the engine and see the full factor breakdown, conviction score,
          and price target framework.
        </motion.p>

        <motion.div
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center h-12 px-8 text-[14px] font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
          >
            See your dashboard
          </Link>
          <Link
            href="/#pricing"
            className="inline-flex items-center justify-center h-12 px-6 text-[14px] font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
          >
            Learn about pricing
          </Link>
        </motion.div>
      </div>
    </section>
  )
}
