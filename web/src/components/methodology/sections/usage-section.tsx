"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const guides = [
  {
    title: "Getting Started",
    desc: "Set up your dashboard and score your first stock",
    href: "/guides/getting-started",
  },
  {
    title: "Reading the Dashboard",
    desc: "Understand every element on your candidate cards",
    href: "/guides/reading-the-dashboard",
  },
  {
    title: "Scoring Factors",
    desc: "Deep dive into all 20 factors across three pillars",
    href: "/guides/scoring-factors",
  },
  {
    title: "Analyzing a Stock",
    desc: "Step-by-step workflow from score to decision",
    href: "/guides/analyzing-a-stock",
  },
]

export function UsageSection() {
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
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Next Steps
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          How to use these outputs.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          The engine replaces the tedious parts of investment analysis — data
          gathering, normalization, cross-factor comparison, and ranking. The
          judgment call on whether to act is always yours. These guides walk
          you through practical workflows.
        </motion.p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {guides.map((guide, i) => (
            <motion.div
              key={guide.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <Link
                href={guide.href}
                className="block p-5 border border-border-primary rounded-lg bg-bg-elevated hover:border-accent/40 transition-colors"
              >
                <h3 className="text-[15px] font-semibold text-text-primary mb-1">
                  {guide.title}
                </h3>
                <p className="text-[13px] text-text-secondary">
                  {guide.desc}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
