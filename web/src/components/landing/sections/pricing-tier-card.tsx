"use client"

import Link from "next/link"
import posthog from "posthog-js"

export interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted?: boolean
}

const CTA_TEXT: Record<string, string> = { Scout: "Search Any Ticker", Analyst: "Start Analyzing", Portfolio: "Start Building" }

export function PricingTierCard({ tier }: { tier: Tier }) {
  const bg = tier.highlighted ? "var(--color-surface-container-high)" : "var(--color-surface-container-low)"

  return (
    <div className="rounded-lg flex flex-col h-full p-6 md:p-8 transition-all duration-200"
      style={{ background: bg, border: "1px solid var(--color-ghost-border)" }}>
      <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>
        {tier.name.toUpperCase()}
        {tier.highlighted && (
          <span className="ml-2 text-label-sm px-2 py-0.5 rounded" style={{ color: "var(--color-primary)", background: "rgba(128, 216, 178, 0.1)" }}>POPULAR</span>
        )}
      </div>

      <div className="mb-2">
        <span className="text-headline-md" style={{ color: "var(--color-on-surface)" }}>{tier.price}</span>
        {tier.period && <span className="text-sm ml-1" style={{ color: "var(--color-text-tertiary)" }}>{tier.period}</span>}
      </div>

      <p className="text-sm mb-1" style={{ color: "var(--color-on-surface-variant)" }}>{tier.description}</p>
      {tier.period ? (
        <p className="text-label-sm mb-6" style={{ color: "var(--color-text-tertiary)" }}>billed {tier.period === "/year" ? "annually" : "monthly"}</p>
      ) : <div className="mb-6" />}

      <div className="flex flex-col gap-3 mb-8 flex-1">
        {tier.features.map((feature) => (
          <div key={feature} className="flex items-start gap-2 text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
            <span style={{ color: "var(--color-primary)" }}>&#10003;</span>
            <span>{feature}</span>
          </div>
        ))}
      </div>

      <Link href="/onboarding" onClick={() => posthog.capture("checkout_started", { plan: tier.name })}
        className="block text-center text-sm font-medium py-2.5 transition-all duration-200"
        style={{
          borderRadius: "0.375rem",
          background: tier.highlighted ? "var(--color-primary-container)" : "transparent",
          color: tier.highlighted ? "var(--color-on-primary-container)" : "var(--color-primary)",
          border: tier.highlighted ? "none" : "1px solid var(--color-ghost-border)",
        }}>
        {CTA_TEXT[tier.name] ?? "Get Started"}
      </Link>
    </div>
  )
}
