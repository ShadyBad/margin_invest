"use client"

import { motion } from "framer-motion"
import Link from "next/link"

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
  badge?: string
  monthlyPrice?: string
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
    badge: "Most popular",
    monthlyPrice: "$39",
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
    monthlyPrice: "$99",
  },
]

function TierCard({ tier, index }: { tier: Tier; index: number }) {
  return (
    <motion.div
      className={`relative flex flex-col p-6 rounded-[6px] border ${
        tier.highlighted
          ? "border-accent bg-gradient-to-t from-bg-elevated to-accent/[0.04]"
          : "border-border-primary bg-bg-primary"
      }`}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1, ease }}
    >
      {tier.badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[11px] font-medium bg-accent text-white px-3 py-1 rounded-full">
          {tier.badge}
        </span>
      )}
      <div className="mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          {tier.name}
        </span>
      </div>
      <div className="flex items-baseline gap-1 mb-1">
        <span className="text-[36px] font-bold text-text-primary leading-none tracking-[-1px]">
          {tier.price}
        </span>
        {tier.period && (
          <span className="text-[15px] text-text-secondary">{tier.period}</span>
        )}
      </div>
      {tier.monthlyPrice && (
        <p className="text-[12px] text-text-tertiary mb-4">
          <span className="line-through">{tier.monthlyPrice}/mo</span>{" "}
          — billed annually, save {Math.round((1 - parseInt(tier.price.replace("$", "")) / parseInt(tier.monthlyPrice.replace("$", ""))) * 100)}%
        </p>
      )}
      {!tier.monthlyPrice && <div className="mb-4" />}
      <p className="text-[14px] text-text-secondary leading-relaxed mb-6">
        {tier.description}
      </p>
      <ul className="flex flex-col gap-2.5 mb-8 flex-1">
        {tier.features.map((feature) => (
          <li
            key={feature}
            className="text-[13px] text-text-secondary flex items-start gap-2"
          >
            <span className="text-accent mt-0.5 flex-shrink-0">&#x2713;</span>
            {feature}
          </li>
        ))}
      </ul>
      <Link
        href={tier.href}
        className={`block text-center text-[14px] font-medium py-3 px-6 rounded-[4px] transition-colors ${
          tier.highlighted
            ? "bg-accent text-white hover:bg-accent-hover"
            : "border border-border-primary text-text-primary hover:bg-bg-subtle"
        }`}
      >
        {tier.cta}
      </Link>
    </motion.div>
  )
}

export function PricingSection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1200px",
          paddingLeft: "10vw",
          paddingRight: "10vw",
          paddingTop: "140px",
          paddingBottom: "140px",
        }}
      >
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[28px] md:text-[32px] lg:text-[40px] font-bold text-text-primary leading-tight tracking-[-0.3px]">
            Simple, transparent pricing.
          </h2>
          <p className="mt-3 text-[15px] text-text-secondary">
            Billed annually. Cancel anytime.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-[960px] mx-auto">
          {tiers.map((tier, i) => (
            <TierCard key={tier.name} tier={tier} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
