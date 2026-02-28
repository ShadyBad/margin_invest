"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const outcomes = [
  "Scores updated daily after market close",
  "Transparent factor breakdowns you can audit",
  "Quantified composite tiers, not subjective ratings",
  "Price targets with explicit margin of safety",
  "Position sizing tied to composite tier strength",
]

export function HeroSection() {
  return (
    <section>
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
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          How It Works
        </motion.p>

        <motion.h1
          className="heading-1 text-text-primary mb-6 max-w-3xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          From 7,000+ stocks to the ones worth your attention.
        </motion.h1>

        <motion.p
          className="text-[16px] sm:text-[17px] text-text-secondary leading-relaxed max-w-2xl mb-6"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Follow one stock through our entire pipeline — every filter, every
          factor, every decision — to see exactly how composite scores are
          built.
        </motion.p>

        <motion.p
          className="text-xs text-text-tertiary font-mono mb-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.12, ease }}
        >
          Pipeline V4 · Updated February 2026
        </motion.p>

        {/* Outcome bullets */}
        <motion.ul
          className="space-y-3 mb-14"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          {outcomes.map((item) => (
            <li key={item} className="flex items-start gap-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="text-accent flex-shrink-0 mt-0.5"
              >
                <path
                  d="M3 8.5L6.5 12L13 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-[14px] sm:text-[15px] text-text-primary">
                {item}
              </span>
            </li>
          ))}
        </motion.ul>

        {/* CTA buttons */}
        <motion.div
          className="flex flex-wrap gap-4"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.24, ease }}
        >
          <a
            href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-bg-primary text-[14px] font-medium rounded-lg hover:opacity-90 transition-opacity"
          >
            Explore dashboard
          </a>
          <a
            href="/guides"
            className="inline-flex items-center gap-2 px-5 py-2.5 border border-border-primary text-text-primary text-[14px] font-medium rounded-lg hover:bg-bg-elevated transition-colors"
          >
            Read guides
          </a>
        </motion.div>
      </div>
    </section>
  )
}
