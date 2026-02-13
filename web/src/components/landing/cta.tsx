"use client"

import Link from "next/link"
import { motion } from "framer-motion"

export function CTA() {
  return (
    <section className="py-24 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="max-w-3xl mx-auto text-center"
      >
        <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-6">
          Ready to find your next conviction bet?
        </h2>
        <p className="text-xl text-text-secondary mb-10">
          No vibes. No narratives. Just data.
        </p>
        <Link
          href="/login"
          className="inline-block px-8 py-4 bg-gold text-bg-primary font-bold text-lg rounded-lg hover:bg-gold-hover transition-colors"
        >
          Start Analyzing
        </Link>
      </motion.div>
    </section>
  )
}
