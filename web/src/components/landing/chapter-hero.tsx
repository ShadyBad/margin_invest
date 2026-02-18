"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

function WordReveal({ text, delay = 0 }: { text: string; delay?: number }) {
  return (
    <>
      {text.split(" ").map((word, i) => (
        <motion.span
          key={i}
          className="inline-block mr-[0.3em]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: delay + i * 0.08, ease }}
        >
          {word}
        </motion.span>
      ))}
    </>
  )
}

export function ChapterHero() {
  return (
    <section id="signal" className="relative h-screen flex items-center justify-center">
      <div className="relative z-10 text-center max-w-3xl mx-auto px-6">
        <motion.h1
          className="font-display text-5xl md:text-7xl lg:text-[88px] leading-[0.95] tracking-[-0.04em] text-[var(--color-text-primary)]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.01 }}
        >
          <WordReveal text="Conviction, Quantified." />
        </motion.h1>

        <motion.p
          className="mt-6 text-lg md:text-xl text-[var(--color-text-secondary)] max-w-xl mx-auto"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 0.6, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
        >
          A deterministic scoring engine that replaces gut feeling with
          structured, quantified investment conviction.
        </motion.p>

        <motion.div
          className="mt-10 flex items-center justify-center gap-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7, ease }}
        >
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium tracking-wide transition-colors hover:bg-[var(--color-accent-hover)]"
          >
            Start Scoring
          </Link>
          <Link
            href="#engine"
            className="inline-flex items-center justify-center h-12 px-6 text-sm font-medium text-[var(--color-text-secondary)] underline underline-offset-4 decoration-[var(--color-border-primary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            See How It Works
          </Link>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        data-scroll-indicator
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ delay: 1.2, duration: 0.6 }}
      >
        <motion.div
          className="w-px h-8 bg-[var(--color-text-tertiary)]"
          animate={{ scaleY: [1, 0.5, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>
    </section>
  )
}
