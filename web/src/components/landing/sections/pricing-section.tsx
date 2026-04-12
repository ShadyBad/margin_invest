"use client"

import { useEffect, useRef, useState } from "react"
import posthog from "posthog-js"
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
    posthog.capture("pricing_page_viewed")
  }, [])

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      // Respect prefers-reduced-motion — skip entrance animations
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

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

      // Cards fan up with scale + y offset
      gsap.set(cards, { opacity: 0, y: 20, scale: 0.97 })
      gsap.set(bottom, { opacity: 0, y: 20 })
      gsap.set(contact, { opacity: 0, y: 20 })

      const st = ScrollTrigger.create({
        trigger: section,
        start: "top 80%",
        once: true,
        onEnter: () => {
          gsap.to(cards, {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.5,
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

        {/* Trust strip — consolidated signals */}
        <div ref={bottomRef} className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-2">
          <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
            <svg className="w-4 h-4 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            No credit card required
          </span>
          <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
            <svg className="w-4 h-4 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            30-day money-back guarantee
          </span>
          <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
            <svg className="w-4 h-4 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <a href="/contact" className="hover:text-text-primary transition-colors">
              API access available
            </a>
          </span>
        </div>

        {/* Daily scoring stat */}
        <div ref={contactRef} className="text-center mt-6">
          <p className="text-xs font-mono text-accent/70">
            Scoring {(totalUniverse ?? 3056).toLocaleString()} US equities daily
          </p>
        </div>
      </div>

      {/* Visual transition to footer */}
      <div
        className="h-24 mt-8"
        style={{
          background: "linear-gradient(to bottom, transparent, var(--color-bg-primary))",
        }}
      />
    </section>
  )
}
