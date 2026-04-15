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
    name: "Scout", monthlyPrice: null, description: "Search any ticker. See what survives.",
    features: ["Unlimited ticker searches", "Composite score + factor bars", "Elimination filter results", "1 full forensic report / month", "5-ticker watchlist"],
    highlighted: false,
  },
  {
    name: "Analyst", monthlyPrice: 19, description: "Full forensic access for serious investors.",
    features: ["Everything in Scout", "Unlimited forensic reports", "90-day score history", "25-ticker watchlist", "Score alerts", "Sector peer comparison"],
    highlighted: true,
  },
  {
    name: "Portfolio", monthlyPrice: 49, description: "The system that runs your portfolio.",
    features: ["Everything in Analyst", "Unlimited history", "Correlation analysis", "Smart Money (13F tracking)", "API access", "Priority support"],
    highlighted: false,
  },
]

function buildTiers(annual: boolean): Tier[] {
  return TIER_DATA.map((t) => {
    if (t.monthlyPrice === null) return { name: t.name, price: "Free", period: "", description: t.description, features: t.features, highlighted: t.highlighted }
    if (annual) {
      const annualPrice = t.monthlyPrice * 10
      return { name: t.name, price: `$${annualPrice}`, period: "/year", description: t.description, features: t.features, highlighted: t.highlighted }
    }
    return { name: t.name, price: `$${t.monthlyPrice}`, period: "/mo", description: t.description, features: t.features, highlighted: t.highlighted }
  })
}

interface PricingSectionProps { totalUniverse?: number }

export function PricingSection({ totalUniverse }: PricingSectionProps) {
  const [annual, setAnnual] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  const tiers = buildTiers(annual)

  useEffect(() => { posthog.capture("pricing_page_viewed") }, [])

  useEffect(() => {
    if (!sectionRef.current) return
    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const section = sectionRef.current
      const cards = cardRefs.current.filter(Boolean) as HTMLDivElement[]
      if (!section || cards.length !== 3) return
      gsap.set(cards, { opacity: 0, y: 32, filter: "blur(8px)" })
      const st = ScrollTrigger.create({ trigger: section, start: "top 78%", once: true,
        onEnter: () => { gsap.to(cards, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.65, stagger: 0.1, ease: "expo.out" }) },
      })
      cleanups.push(() => st.kill())
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  return (
    <section ref={sectionRef} id="pricing" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-headline-md uppercase text-center mb-4" style={{ color: "var(--color-on-surface)" }}>Choose Your Aperture</h2>
        <p className="text-body-md text-center max-w-md mx-auto mb-10" style={{ color: "var(--color-on-surface-variant)" }}>Upgrade when the data changes how you think.</p>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-1 mb-12 p-1 rounded-lg mx-auto w-fit" style={{ background: "var(--color-surface-container-lowest)" }}>
          <button type="button" onClick={() => setAnnual(false)} className="text-sm font-medium px-4 py-1.5 rounded-md transition-all duration-200" aria-pressed={!annual}
            style={{ background: !annual ? "var(--color-primary-container)" : "transparent", color: !annual ? "var(--color-on-primary-container)" : "var(--color-text-tertiary)" }}>Monthly</button>
          <button type="button" onClick={() => setAnnual(true)} className="text-sm font-medium px-4 py-1.5 rounded-md transition-all duration-200 inline-flex items-center gap-2" aria-pressed={annual}
            style={{ background: annual ? "var(--color-primary-container)" : "transparent", color: annual ? "var(--color-on-primary-container)" : "var(--color-text-tertiary)" }}>
            Annual
            <span className="text-label-sm px-1.5 py-0.5 rounded" style={{ color: "var(--color-bullish)", background: "rgba(34,197,94,0.12)" }}>2 FREE</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {tiers.map((tier, i) => (
            <div key={tier.name} ref={(el) => { cardRefs.current[i] = el }}>
              <PricingTierCard tier={tier} />
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 mt-4">
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>NO CREDIT CARD REQUIRED</span>
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>30-DAY GUARANTEE</span>
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>API AVAILABLE</span>
        </div>

        <div className="text-center mt-6">
          <p className="text-label-sm" style={{ color: "var(--color-primary)" }}>
            Scoring {(totalUniverse ?? 3056).toLocaleString()} US equities daily
          </p>
        </div>
      </div>
    </section>
  )
}
