"use client"

import { useEffect, useRef, useState } from "react"
import { PricingTierCard, type Tier } from "./pricing-tier-card"

interface TierBase {
  name: string
  monthlyPrice: number | null
  description: string
  features: string[]
  highlighted: boolean
}

const TIER_DATA: TierBase[] = [
  {
    name: "Scout",
    monthlyPrice: null,
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
    monthlyPrice: 19,
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
    monthlyPrice: 49,
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

function buildTiers(annual: boolean): Tier[] {
  return TIER_DATA.map((t) => {
    if (t.monthlyPrice === null) {
      return {
        name: t.name,
        price: "Free",
        period: "",
        description: t.description,
        features: t.features,
        highlighted: t.highlighted,
      }
    }
    if (annual) {
      const annualPrice = t.monthlyPrice * 10
      return {
        name: t.name,
        price: `$${annualPrice}`,
        period: "/year",
        description: t.description,
        features: t.features,
        highlighted: t.highlighted,
      }
    }
    return {
      name: t.name,
      price: `$${t.monthlyPrice}`,
      period: "/mo",
      description: t.description,
      features: t.features,
      highlighted: t.highlighted,
    }
  })
}

interface PricingSectionProps {
  totalUniverse?: number
}

export function PricingSection({ totalUniverse }: PricingSectionProps) {
  const [annual, setAnnual] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const contactRef = useRef<HTMLDivElement>(null)

  const tiers = buildTiers(annual)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const section = sectionRef.current
      const cards = cardRefs.current.filter(Boolean) as HTMLDivElement[]
      const bottom = bottomRef.current
      const contact = contactRef.current
      if (!section || cards.length !== 3 || !bottom || !contact) return

      // Simple viewport-enter fade-in with stagger
      gsap.set(cards, { opacity: 0, y: 20 })
      gsap.set(bottom, { opacity: 0, y: 20 })
      gsap.set(contact, { opacity: 0, y: 20 })

      const st = ScrollTrigger.create({
        trigger: section,
        start: "top 80%",
        once: true,
        onEnter: () => {
          // Headline is already visible; fade in cards with stagger
          gsap.to(cards, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            stagger: 0.12,
            ease: "power2.out",
          })
          gsap.to(bottom, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            delay: 0.5,
            ease: "power2.out",
          })
          gsap.to(contact, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            delay: 0.6,
            ease: "power2.out",
          })
        },
      })

      cleanups.push(() => st.kill())
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      cleanups.forEach((fn) => fn())
    }
  }, [])

  return (
    <section ref={sectionRef} id="pricing" className="px-6">
      <div className="max-w-6xl mx-auto flex flex-col justify-center py-20">
        {/* Headline block */}
        <div className="text-center mb-12">
          <h2
            className="font-display text-text-primary text-center mb-3"
            style={{ fontSize: "clamp(36px, 5vw, 48px)" }}
          >
            Start free. Full access from $19/month.
          </h2>
          <p className="text-base text-text-secondary text-center max-w-md mx-auto">
            Upgrade when the data changes how you think.
          </p>
        </div>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3 mb-10" data-billing-toggle>
          <button
            type="button"
            onClick={() => setAnnual(false)}
            className={`text-sm font-medium px-4 py-1.5 rounded-lg transition-colors ${
              !annual
                ? "bg-bg-elevated text-text-primary"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
            aria-pressed={!annual}
          >
            Monthly
          </button>
          <button
            type="button"
            onClick={() => setAnnual(true)}
            className={`text-sm font-medium px-4 py-1.5 rounded-lg transition-colors inline-flex items-center gap-2 ${
              annual
                ? "bg-bg-elevated text-text-primary"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
            aria-pressed={annual}
          >
            Annual
            <span
              className="text-xs px-1.5 py-0.5 rounded font-mono"
              style={{
                color: "var(--color-bullish)",
                background: "color-mix(in srgb, var(--color-bullish) 12%, transparent)",
              }}
            >
              2 months free
            </span>
          </button>
        </div>

        {/* Cards container */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {tiers.map((tier, i) => (
            <div
              key={tier.name}
              ref={(el) => {
                cardRefs.current[i] = el
              }}
            >
              <PricingTierCard tier={tier} />
            </div>
          ))}
        </div>

        {/* Bottom text */}
        <div ref={bottomRef} className="text-center space-y-3">
          <p className="text-sm text-text-secondary">
            No credit card required &middot; 30-day money-back guarantee on all
            paid plans.
          </p>
          <p className="text-xs font-mono text-accent/70 mt-4">
            Scoring {(totalUniverse ?? 3056).toLocaleString()} US equities daily
          </p>
        </div>

        {/* Contact CTA */}
        <div
          ref={contactRef}
          className="mt-10 pt-6 border-t border-border-subtle text-center"
        >
          <p className="text-sm text-text-secondary">
            Need API access or custom integration?{" "}
            <a
              href="/contact"
              className="text-accent hover:text-accent/80 transition-colors"
            >
              Contact us →
            </a>
          </p>
        </div>
      </div>
    </section>
  )
}
