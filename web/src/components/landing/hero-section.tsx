"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { HeroCandidatePanel } from "./hero-candidate-panel"

const ease = [0.22, 1, 0.36, 1] as const

const words = ["Conviction.", "Engineered."]

interface HeroSectionProps {
  pick: Parameters<typeof HeroCandidatePanel>[0]["pick"]
}

export function HeroSection({ pick }: HeroSectionProps) {
  return (
    <section
      id="hero"
      className="min-h-screen flex items-center justify-center px-6"
      style={{
        background: "linear-gradient(180deg, #0A0F0D 0%, #0D1510 100%)",
      }}
    >
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* Left: headline + CTAs */}
        <div>
          <h1 className="font-display text-5xl md:text-7xl lg:text-[88px] leading-[0.95] tracking-[-0.04em] text-text-primary mb-6">
            {words.map((word, i) => (
              <motion.span
                key={word}
                className="inline-block mr-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: i * 0.12, ease }}
              >
                {word}
              </motion.span>
            ))}
          </h1>

          <motion.p
            className="text-lg text-text-secondary max-w-md mb-10 leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4, ease }}
          >
            A deterministic capital allocation system that replaces narrative with structure.
          </motion.p>

          <motion.div
            className="flex items-center gap-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-accent text-white text-sm font-medium tracking-wide transition-colors hover:bg-accent-hover"
            >
              Open the Dashboard
            </Link>
            <Link
              href="/methodology"
              className="text-sm font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
            >
              See the Methodology
            </Link>
          </motion.div>
        </div>

        {/* Right: candidate panel */}
        <div className="flex justify-center lg:justify-end">
          <HeroCandidatePanel pick={pick} />
        </div>
      </div>
    </section>
  )
}
