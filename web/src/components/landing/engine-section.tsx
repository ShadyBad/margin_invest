"use client"

import { useRef, useState, useEffect } from "react"
import { PipelineDiagram } from "./pipeline-diagram"
import { EngineCard } from "./engine-card"

const topRowCards = [
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

const bottomRowCards = [
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
    title: "Conviction Score Synthesis",
    subtitle: "Output",
    description:
      "Weighted combination of factor percentiles produces a single composite conviction score. Growth stage adjusts weights automatically.",
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

export function EngineSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const topRowRef = useRef<HTMLDivElement>(null)
  const bottomRowRef = useRef<HTMLDivElement>(null)
  const [activeStage, setActiveStage] = useState(0)

  useEffect(() => {
    let gsapModule: any
    let ScrollTriggerModule: any

    async function initGSAP() {
      try {
        gsapModule = (await import("gsap")).default
        ScrollTriggerModule = (await import("gsap/ScrollTrigger")).default
        gsapModule.registerPlugin(ScrollTriggerModule)

        if (!sectionRef.current || !topRowRef.current || !bottomRowRef.current) return

        // Top row scrolls left
        gsapModule.to(topRowRef.current, {
          x: "-30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Bottom row scrolls right
        gsapModule.to(bottomRowRef.current, {
          x: "30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Pipeline stage highlighting
        ScrollTriggerModule.create({
          trigger: sectionRef.current,
          start: "top center",
          end: "bottom center",
          onUpdate: (self: any) => {
            const progress = self.progress
            const stage = Math.min(5, Math.floor(progress * 6))
            setActiveStage(stage)
          },
        })
      } catch {
        // GSAP not available — graceful degradation
      }
    }

    initGSAP()

    return () => {
      if (ScrollTriggerModule) {
        ScrollTriggerModule.getAll?.().forEach((t: any) => t.kill())
      }
    }
  }, [])

  return (
    <section ref={sectionRef} id="engine" className="relative py-24 overflow-hidden">
      {/* Sticky pipeline diagram */}
      <div className="sticky top-20 z-10 bg-bg-primary/80 backdrop-blur-sm py-4 mb-12">
        <PipelineDiagram activeStage={activeStage} />
      </div>

      {/* Desktop: counter-scrolling card rows */}
      <div className="hidden md:block space-y-8">
        <div
          ref={topRowRef}
          data-card-row
          data-direction="left"
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(30%)" }}
        >
          {topRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>

        <div
          ref={bottomRowRef}
          data-card-row
          data-direction="right"
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(-30%)" }}
        >
          {bottomRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>
      </div>

      {/* Mobile: vertical interleaved stack */}
      <div className="md:hidden flex flex-col items-center gap-4 px-6 max-w-[360px] mx-auto">
        {topRowCards.map((card, i) => (
          <div key={card.title} className="w-full space-y-4">
            <EngineCard {...card} />
            {bottomRowCards[i] && <EngineCard {...bottomRowCards[i]} />}
          </div>
        ))}
      </div>
    </section>
  )
}
