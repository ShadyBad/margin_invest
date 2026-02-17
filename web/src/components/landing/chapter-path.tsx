"use client"

import Link from "next/link"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"
import { GlassSurface } from "../ui/glass-surface"

const ease = [0.22, 1, 0.36, 1] as const

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  cta: string
  href: string
  highlighted: boolean
}

const tiers: Tier[] = [
  {
    name: "Scout",
    price: "Free",
    period: "",
    description: "Evaluate the engine with real positions.",
    features: [
      "3 ticker analyses per month",
      "Composite score + conviction level",
      "Top-level factor breakdown",
      "5-ticker watchlist",
    ],
    cta: "Start free",
    href: "/onboarding",
    highlighted: false,
  },
  {
    name: "Operator",
    price: "$29",
    period: "/mo",
    description: "Full scoring for active portfolio management.",
    features: [
      "Unlimited ticker analysis",
      "Full 6-factor breakdown",
      "90-day score history",
      "25-ticker watchlist",
      "Conviction change alerts",
    ],
    cta: "Start trial",
    href: "/onboarding",
    highlighted: true,
  },
  {
    name: "Allocator",
    price: "$79",
    period: "/mo",
    description: "Portfolio-level conviction infrastructure.",
    features: [
      "Everything in Operator",
      "Unlimited score history",
      "Portfolio correlation analysis",
      "Sector rotation signals",
      "API access",
    ],
    cta: "Get started",
    href: "/onboarding",
    highlighted: false,
  },
]

function TierCard({ tier, index }: { tier: Tier; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.12, ease }}
    >
      <GlassSurface
        elevated={tier.highlighted}
        className={`p-6 md:p-8 flex flex-col ${tier.highlighted ? "-mt-4 mb-4 md:-mt-6 md:mb-6" : ""}`}
      >
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-text-tertiary)] mb-3">
          {tier.name}
        </p>
        <div className="flex items-baseline gap-1 mb-2">
          <span className="font-display text-4xl text-[var(--color-text-primary)]">
            {tier.price}
          </span>
          {tier.period && (
            <span className="text-sm text-[var(--color-text-tertiary)]">{tier.period}</span>
          )}
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] mb-6">{tier.description}</p>
        <ul className="space-y-2 mb-8 flex-1">
          {tier.features.map((f) => (
            <li key={f} className="text-sm text-[var(--color-text-secondary)] flex items-start gap-2">
              <span className="text-[var(--color-accent)] mt-0.5">&#x2713;</span>
              {f}
            </li>
          ))}
        </ul>
        <Link
          href={tier.href}
          className={`inline-flex items-center justify-center h-11 rounded-lg text-sm font-medium transition-colors ${
            tier.highlighted
              ? "bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]"
              : "border border-[var(--color-border-primary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-subtle)]"
          }`}
        >
          {tier.cta}
        </Link>
      </GlassSurface>
    </motion.div>
  )
}

export function ChapterPath() {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-6 py-24">
      <motion.h2
        className="font-display text-4xl md:text-5xl text-center text-[var(--color-text-primary)] mb-4"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease }}
      >
        Start Building Conviction
      </motion.h2>
      <motion.p
        className="text-[var(--color-text-secondary)] text-center max-w-lg mb-16"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 0.7 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.15, ease }}
      >
        Choose the lens that fits how you invest.
      </motion.p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full items-start">
        {tiers.map((tier, i) => (
          <TierCard key={tier.name} tier={tier} index={i} />
        ))}
      </div>

      <motion.div
        className="mt-20 text-center"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.4, ease }}
      >
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium tracking-wide transition-colors hover:bg-[var(--color-accent-hover)]"
        >
          Start Scoring
        </Link>
        <p className="mt-4 text-xs text-[var(--color-text-tertiary)]">
          No credit card required for Scout tier.
        </p>
      </motion.div>
    </section>
  )
}
