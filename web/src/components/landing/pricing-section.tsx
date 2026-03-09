"use client"

import { useEffect, useRef } from "react"
import { PricingTierCard, type Tier } from "./pricing-tier-card"
import { useScrollCanvas } from "./scroll-canvas"

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
  const { isSmoothScrolling } = useScrollCanvas()
  const sectionRef = useRef<HTMLElement>(null)
  const headlineRef = useRef<HTMLDivElement>(null)
  const cardsContainerRef = useRef<HTMLDivElement>(null)
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const contactRef = useRef<HTMLDivElement>(null)

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
      const headline = headlineRef.current
      const cardsContainer = cardsContainerRef.current
      const cards = cardRefs.current.filter(Boolean) as HTMLDivElement[]
      const bottom = bottomRef.current
      const contact = contactRef.current
      if (!section || !headline || !cardsContainer || cards.length !== 3 || !bottom || !contact)
        return

      // ── Mobile / no-smooth path: simple viewport-enter fade-in ──
      if (!isSmoothScrolling) {
        // Show all content immediately — no pinning, no split animation
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
        return
      }

      // ── Desktop / smooth-scroll path: pinned sequential reveal ──

      const h2 = headline.querySelector("h2")
      const subtitle = headline.querySelector("p")

      // Gather feature <li> elements and CTA buttons within each card
      const featureSets = cards.map((card) =>
        Array.from(card.querySelectorAll<HTMLElement>("li"))
      )
      const ctaButtons = cards.map((card) =>
        card.querySelector<HTMLElement>("a")
      )

      // Initial states
      gsap.set(headline, { opacity: 1 })
      gsap.set(cards, { opacity: 0 })
      featureSets.forEach((features) => {
        gsap.set(features, { opacity: 0 })
        features.forEach((li) => {
          const check = li.querySelector("span:first-child")
          if (check) gsap.set(check, { scale: 0, transformOrigin: "center" })
        })
      })
      ctaButtons.forEach((btn) => {
        if (btn) gsap.set(btn, { opacity: 0 })
      })
      gsap.set(bottom, { opacity: 0, y: 20 })
      gsap.set(contact, { opacity: 0, y: 20 })

      // Build the master pinned timeline (~150vh travel)
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: "+=150%",
          pin: true,
          scrub: 0.5,
          anticipatePin: 1,
        },
      })

      // ── Phase 1 (0-20%): Headline alone, centered ──
      // Headline is already visible; hold it for a beat
      tl.to({}, { duration: 20 }, 0)

      // ── Phase 2 (20-50%): Headline fades up, cards split outward ──
      // Fade headline
      if (h2) tl.to(h2, { opacity: 0.3, y: -30, duration: 12, ease: "power2.inOut" }, 20)
      if (subtitle) tl.to(subtitle, { opacity: 0, y: -20, duration: 8, ease: "power2.inOut" }, 20)

      // Set initial card positions before defining tweens
      gsap.set(cards[0], { x: 80, opacity: 0 })
      gsap.set(cards[1], { y: 40, opacity: 0 })
      gsap.set(cards[2], { x: -80, opacity: 0 })

      // Scout slides left
      tl.to(cards[0], { opacity: 1, x: 0, duration: 15, ease: "power2.out" }, 22)

      // Analyst rises center (100ms stagger = +1 unit)
      tl.to(cards[1], { opacity: 1, y: 0, duration: 15, ease: "power2.out" }, 23)

      // Portfolio slides right (200ms stagger = +2 units)
      tl.to(cards[2], { opacity: 1, x: 0, duration: 15, ease: "power2.out" }, 24)

      // ── Phase 3 (50-85%): Features fill in sequentially ──
      const featureStart = 50
      let featureTime = featureStart

      for (let cardIdx = 0; cardIdx < 3; cardIdx++) {
        const features = featureSets[cardIdx]
        features.forEach((li) => {
          // Fade in the feature text
          tl.to(li, { opacity: 1, duration: 2, ease: "power2.out" }, featureTime)
          // Pop the checkmark with back ease
          const check = li.querySelector("span:first-child")
          if (check) {
            tl.to(
              check,
              { scale: 1, duration: 1.5, ease: "back.out(1.7)" },
              featureTime
            )
          }
          featureTime += 1.5
        })
      }

      // CTA buttons fade in last
      const ctaStart = Math.max(featureTime, 75)
      ctaButtons.forEach((btn, i) => {
        if (btn) {
          tl.to(btn, { opacity: 1, duration: 3, ease: "power2.out" }, ctaStart + i * 1)
        }
      })

      // ── Phase 4 (85-100%): Unpin. Bottom text + contact fade in ──
      tl.to(bottom, { opacity: 1, y: 0, duration: 6, ease: "power2.out" }, 85)
      tl.to(contact, { opacity: 1, y: 0, duration: 6, ease: "power2.out" }, 88)

      // Extend to 100
      tl.to({}, { duration: 5 }, 95)

      // Store cleanup
      const st = tl.scrollTrigger
      cleanups.push(() => {
        tl.kill()
        st?.kill()
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      cleanups.forEach((fn) => fn())
    }
  }, [isSmoothScrolling])

  return (
    <section ref={sectionRef} id="pricing" className="px-6">
      <div className="max-w-5xl mx-auto flex flex-col justify-center min-h-screen py-20">
        {/* Headline block — starts full-viewport centered */}
        <div ref={headlineRef} className="text-center mb-16">
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

        {/* Cards container */}
        <div
          ref={cardsContainerRef}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10"
        >
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
            Scoring 3,056 US equities daily
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
