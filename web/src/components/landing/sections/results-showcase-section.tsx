"use client"

import { useEffect, useRef } from "react"
import type { HomepageData, CandidateCard } from "../shared/types"
import { FactorBars } from "../visualizations/factor-bars"
import { formatScore } from "@/lib/format"

interface ResultsShowcaseSectionProps {
  data: HomepageData | null
}

function timeAgo(iso: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(iso).getTime()) / 1000
  )
  if (seconds < 60) return "just now"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

/**
 * Returns the CSS color variable for a given composite tier.
 */
function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional":
      return "var(--color-percentile-exceptional)"
    case "high":
      return "var(--color-percentile-strong)"
    case "moderate":
      return "var(--color-percentile-average)"
    case "low":
      return "var(--color-percentile-below)"
    case "very_low":
      return "var(--color-percentile-weak)"
    default:
      return "var(--color-text-secondary)"
  }
}

function CandidateCardItem({ candidate }: { candidate: CandidateCard }) {
  return (
    <div className="terminal-card p-5 flex flex-col gap-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_8px_24px_rgba(26,122,90,0.12)] hover:border-accent/30">
      {/* Ticker + Name */}
      <div>
        <div className="text-title-1 font-bold text-text-primary">
          {candidate.ticker}
        </div>
        <div className="text-caption text-text-secondary truncate">
          {candidate.name}
        </div>
      </div>

      {/* Composite score — color-encoded by tier */}
      <div
        className="text-mono-data font-bold transition-transform duration-200 hover:scale-105 origin-left cursor-default"
        style={{ color: getTierColor(candidate.composite_tier) }}
      >
        {formatScore(candidate.score)}
      </div>

      {/* 5 factor bars (compact) */}
      <FactorBars
        factors={{
          quality: candidate.quality_percentile,
          value: candidate.value_percentile,
          momentum: candidate.momentum_percentile,
          sentiment: candidate.sentiment_percentile,
          growth: candidate.growth_percentile,
        }}
        compact
      />

      {/* Sector pill + freshness timestamp */}
      <div className="flex items-center gap-2 mt-auto pt-2">
        <span className="text-mono-label bg-white/5 text-text-tertiary px-2 py-0.5 rounded">
          {candidate.sector}
        </span>
        <span className="text-caption text-text-tertiary">
          {timeAgo(candidate.scored_at)}
        </span>
      </div>
    </div>
  )
}

export function ResultsShowcaseSection({ data }: ResultsShowcaseSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const cards = el.querySelectorAll("[data-result-card]")
      if (cards.length === 0) return

      gsap.set(cards, { opacity: 0, y: 30 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(cards, {
            opacity: 1,
            y: 0,
            duration: 0.5,
            ease: "power2.out",
            stagger: 0.15,
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  // Null data — engine hasn't run yet
  if (!data) {
    return (
      <section id="results" className="bg-bg-subtle py-20 px-6">
        <div className="max-w-6xl mx-auto text-center text-text-secondary text-sm">
          Scoring data loads after the engine completes a cycle.
        </div>
      </section>
    )
  }

  // Empty candidates — cycle in progress
  if (data.candidates.length === 0) {
    return (
      <section id="results" className="bg-bg-subtle py-20 px-6">
        <div className="max-w-6xl mx-auto text-center text-text-secondary text-sm">
          Scoring in progress — results appear after each cycle.
        </div>
      </section>
    )
  }

  const top3 = data.candidates.slice(0, 3)
  const eliminated = data.total_universe - data.eligible_count
  const totalUniverse = data.total_universe
  const totalScored = data.total_scored
  const survivingCount = data.surviving_count

  return (
    <section id="results" ref={sectionRef} className="bg-bg-subtle py-20 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Monospace header with status dot */}
        <div className="flex items-center gap-2 mb-8">
          <span className="inline-block w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="text-mono-label text-text-tertiary">
            CURRENT CYCLE RESULTS
          </span>
        </div>

        {/* 3 candidate cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {top3.map((candidate) => (
            <div key={candidate.ticker} data-result-card>
              <CandidateCardItem candidate={candidate} />
            </div>
          ))}
        </div>

        {/* Summary stat line */}
        <div className="mt-8 text-center">
          <span className="text-mono-label text-text-tertiary">
            {totalUniverse.toLocaleString("en-US")} scanned
            {" · "}
            {eliminated.toLocaleString("en-US")} eliminated
            {" · "}
            {totalScored.toLocaleString("en-US")} scored
            {" · "}
            {survivingCount.toLocaleString("en-US")} survived
          </span>
        </div>
      </div>
    </section>
  )
}
