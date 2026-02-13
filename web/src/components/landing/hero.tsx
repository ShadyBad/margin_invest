"use client"

import Link from "next/link"
import { motion } from "framer-motion"

export function Hero() {
  return (
    <section className="min-h-screen flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center max-w-4xl"
      >
        <h1 className="text-5xl md:text-7xl font-bold text-text-primary mb-6">
          Find <span className="text-gold">once-in-a-generation</span> investment bets
        </h1>
        <p className="text-xl md:text-2xl text-text-secondary mb-10 max-w-2xl mx-auto">
          Deterministic analysis. Zero human bias. Same inputs, same outputs, every time.
        </p>
        <Link
          href="/login"
          className="inline-block px-8 py-4 bg-gold text-bg-primary font-bold text-lg rounded-lg hover:bg-gold-hover transition-colors"
        >
          Get Started
        </Link>
      </motion.div>
    </section>
  )
}
