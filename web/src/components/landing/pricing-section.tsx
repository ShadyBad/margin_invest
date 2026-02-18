"use client"

import Link from "next/link"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const ease = [0.22, 1, 0.36, 1] as const

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted: boolean
}

const tiers: Tier[] = [
  {
    name: "Analyst",
    price: "Free",
    period: "",
    description: "Evaluate the engine with real positions.",
    features: [
      "3 ticker analyses per month",
      "Composite score + conviction level",
      "Top-level factor breakdown",
      "5-ticker watchlist",
    ],
    highlighted: false,
  },
  {
    name: "Portfolio",
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
    highlighted: true,
  },
  {
    name: "Institutional",
    price: "$79",
    period: "/mo",
    description: "Portfolio-level conviction infrastructure.",
    features: [
      "Everything in Portfolio",
      "Unlimited score history",
      "Portfolio correlation analysis",
      "Sector rotation signals",
      "API access",
    ],
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
      className={tier.highlighted ? "-mt-4 mb-4 md:-mt-6 md:mb-6" : ""}
    >
      <div
        className={
          tier.highlighted
            ? "terminal-card-accent p-6 md:p-8 flex flex-col"
            : "terminal-card p-6 md:p-8 flex flex-col"
        }
      >
        <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-3">{tier.name}</p>
        <div className="flex items-baseline gap-1 mb-2">
          <span className="font-display text-4xl text-text-primary">{tier.price}</span>
          {tier.period && <span className="text-sm text-text-tertiary">{tier.period}</span>}
        </div>
        <p className="text-sm text-text-secondary mb-6">{tier.description}</p>
        <ul className="space-y-2 mb-8 flex-1">
          {tier.features.map((f) => (
            <li key={f} className="text-sm text-text-secondary flex items-start gap-2">
              <span className="text-accent mt-0.5">&#x2713;</span>
              {f}
            </li>
          ))}
        </ul>
        <Link
          href="/onboarding"
          className={`inline-flex items-center justify-center h-11 rounded-lg text-sm font-medium transition-colors ${
            tier.highlighted
              ? "bg-accent text-white hover:bg-accent-hover"
              : "border border-border-primary text-text-primary hover:bg-bg-subtle"
          }`}
        >
          {tier.highlighted ? "Start trial" : tier.price === "Free" ? "Start free" : "Get started"}
        </Link>
      </div>
    </motion.div>
  )
}

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <p className="text-sm uppercase tracking-[0.15em] text-text-tertiary text-center mb-6">
          The system scales with your responsibility.
        </p>

        <motion.h2
          className="font-display text-4xl md:text-5xl text-center text-text-primary mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Start Building Conviction
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
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
            className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-accent text-white text-sm font-medium tracking-wide transition-colors hover:bg-accent-hover"
          >
            Start Building Conviction
          </Link>
          <p className="mt-4 text-xs text-text-tertiary">
            No credit card required for Analyst tier.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
