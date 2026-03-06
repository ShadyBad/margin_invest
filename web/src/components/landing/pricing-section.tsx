"use client"

import { PricingTierCard, type Tier } from "./pricing-tier-card"

const tiers: Tier[] = [
  {
    name: "Scout",
    price: "Free",
    period: "",
    description: "Search any ticker. See what survives.",
    features: [
      "Unlimited ticker searches",
      "Composite score + factor bars",
      "Elimination filter results",
      "1 full forensic report / month",
      "5-ticker watchlist",
    ],
    highlighted: false,
  },
  {
    name: "Analyst",
    price: "$19",
    period: "/mo",
    description: "Full forensic access for serious investors.",
    features: [
      "Everything in Scout",
      "Unlimited forensic reports",
      "90-day score history",
      "25-ticker watchlist",
      "Score alerts",
      "Sector peer comparison",
    ],
    highlighted: true,
  },
  {
    name: "Portfolio",
    price: "$49",
    period: "/mo",
    description: "The system that runs your portfolio.",
    features: [
      "Everything in Analyst",
      "Unlimited history",
      "Correlation analysis",
      "Smart Money (13F tracking)",
      "API access",
      "Priority support",
    ],
    highlighted: false,
  },
]

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 px-6" style={{ background: 'linear-gradient(180deg, transparent 0%, var(--color-accent-warm-muted) 50%, transparent 100%)' }}>
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-3xl md:text-4xl text-text-primary text-center mb-3">
          Invest in your process, not another guru.
        </h2>
        <p className="text-base text-text-secondary text-center mb-16 max-w-md mx-auto">
          Start free. Upgrade when the data changes how you think.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {tiers.map((tier) => (
            <PricingTierCard key={tier.name} tier={tier} />
          ))}
        </div>
        <div className="text-center space-y-3">
          <p className="text-sm text-text-secondary">
            30-day money-back guarantee on all paid plans. No questions.
          </p>
          <p className="text-xs text-text-tertiary">
            Founding members lock in this price forever. Pricing increases after launch.
          </p>
        </div>
      </div>
    </section>
  )
}
