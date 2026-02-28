"use client"

import { useEffect, useRef } from "react"
import { EngineCard } from "./engine-card"

interface EngineSectionProps {
  onStageChange: (stage: number) => void
}

interface CardData {
  title: string
  subtitle: string
  description: string
}

const topRowCards: CardData[] = [
  {
    title: "Raw Market Signal",
    subtitle: "Input",
    description:
      "Earnings transcripts, SEC filings, price targets, institutional flows — hundreds of data points per ticker, gathered and normalized.",
  },
  {
    title: "Data Integrity + Normalization",
    subtitle: "Input",
    description:
      "Standardize across reporting periods, currencies, and accounting methods. Clean data is the foundation of deterministic scoring.",
  },
  {
    title: "Elimination Filters",
    subtitle: "Gating",
    description:
      "Penny stocks, delistings, insufficient data — fail-fast filters eliminate noise before scoring begins. Only investable assets proceed.",
  },
  {
    title: "Survivorship Bias Control",
    subtitle: "Gating",
    description:
      "Delisted and acquired companies remain in historical datasets. No retroactive cleaning of failures from the record.",
  },
  {
    title: "Liquidity Thresholding",
    subtitle: "Gating",
    description:
      "Minimum volume and market cap requirements ensure every scored asset is actually tradeable at institutional scale.",
  },
]

const bottomRowCards: CardData[] = [
  {
    title: "Multi-Factor Ranking",
    subtitle: "Scoring",
    description:
      "Five factors — valuation, quality, momentum, growth, sentiment — each scored independently against sector peers.",
  },
  {
    title: "Percentile Normalization",
    subtitle: "Scoring",
    description:
      "Raw scores converted to percentile ranks (0-100) within GICS sector. Cross-factor comparison becomes meaningful.",
  },
  {
    title: "Composite Score Synthesis",
    subtitle: "Output",
    description:
      "Weighted combination of factor percentiles produces a single composite score. Growth stage adjusts weights automatically.",
  },
  {
    title: "Sector-Neutral Construction",
    subtitle: "Output",
    description:
      "Rank within sector first, then combine. A 60th-percentile bank is compared to banks, not tech stocks.",
  },
  {
    title: "Portfolio Correlation Mapping",
    subtitle: "Output",
    description:
      "Identify correlated positions across your portfolio. Diversification measured, not assumed.",
  },
]

export function EngineSection({ onStageChange }: EngineSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const topRowRef = useRef<HTMLDivElement>(null)
  const bottomRowRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default

      gsap.registerPlugin(ScrollTrigger)

      const section = sectionRef.current
      const topRow = topRowRef.current
      const bottomRow = bottomRowRef.current
      if (!section || !topRow || !bottomRow) return

      // Top row: scroll left
      const topTrigger = ScrollTrigger.create({
        trigger: section,
        start: "top center",
        end: "bottom center",
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress
          const xTop = 30 - progress * 60
          const xBottom = -30 + progress * 60
          gsap.set(topRow, { xPercent: xTop })
          gsap.set(bottomRow, { xPercent: xBottom })
        },
      })
      triggers.push(topTrigger)

      // Pipeline stage sync — all 6 stages complete within ~75% of section scroll
      const stageTrigger = ScrollTrigger.create({
        trigger: section,
        start: "top 70%",
        end: "80% center",
        onUpdate: (self) => {
          const stage = Math.min(5, Math.floor(self.progress * 7.5))
          onStageChange(stage)
        },
        onLeaveBack: () => onStageChange(0),
      })
      triggers.push(stageTrigger)
    }

    animate().catch(() => {
      // Silently handle module resolution failures during test teardown
    })

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [onStageChange])

  return (
    <section id="engine" ref={sectionRef} className="py-24 overflow-hidden">
      {/* Desktop: two counter-scrolling rows */}
      <div className="hidden md:block relative">
        <div
          ref={topRowRef}
          className="flex gap-6 mb-6"
          style={{ transform: "translateX(30%)" }}
        >
          {topRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>

        {/* Faint connection line */}
        <div className="absolute left-0 right-0 h-px bg-accent/[0.08]" style={{ top: "50%" }} />

        <div
          ref={bottomRowRef}
          className="flex gap-6"
          style={{ transform: "translateX(-30%)" }}
        >
          {bottomRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>
      </div>

      {/* Mobile: vertical interleaved stack */}
      <div className="md:hidden space-y-4 px-4">
        {topRowCards.map((card, i) => (
          <div key={card.title}>
            <EngineCard {...card} />
            {bottomRowCards[i] && (
              <div className="mt-4">
                <EngineCard {...bottomRowCards[i]} />
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
