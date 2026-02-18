"use client"

import { PricingTierCard, type Tier } from "./pricing-tier-card"

const tiers: Tier[] = [
  {
    name: "Analyst",
    price: "Free",
    period: "",
    description: "Start analyzing with the core scoring engine.",
    features: [
      "3 analyses per month",
      "Composite score",
      "Top-level breakdown",
      "5-ticker watchlist",
    ],
    highlighted: false,
  },
  {
    name: "Portfolio",
    price: "$29",
    period: "/mo",
    description: "Full factor access for active portfolio managers.",
    features: [
      "Unlimited analysis",
      "Full 6-factor breakdown",
      "90-day history",
      "25-ticker watchlist",
      "Conviction alerts",
    ],
    highlighted: true,
  },
  {
    name: "Institutional",
    price: "$79",
    period: "/mo",
    description: "Enterprise-grade tools for allocators and teams.",
    features: [
      "Everything in Portfolio",
      "Unlimited history",
      "Correlation analysis",
      "Sector rotation",
      "API access",
    ],
    highlighted: false,
  },
]

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <p className="text-sm uppercase tracking-[0.2em] text-text-tertiary text-center mb-16">
          The system scales with your responsibility.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tiers.map((tier) => (
            <PricingTierCard key={tier.name} tier={tier} />
          ))}
        </div>
      </div>
    </section>
  )
}
