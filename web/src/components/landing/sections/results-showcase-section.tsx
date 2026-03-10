"use client"

import { useEffect, useRef } from "react"
import type { HomepageData, CandidateCard } from "../shared/types"

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

interface FactorBarProps {
  label: string
  value: number
}

function FactorBar({ label, value }: FactorBarProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20">{label}</span>
      <div className="relative flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="font-mono text-xs w-8 text-right text-text-secondary">
        {value}
      </span>
    </div>
  )
}

function CandidateColumn({ candidate }: { candidate: CandidateCard }) {
  return (
    <div className="p-5 flex flex-col gap-3">
      {/* Ticker + Name */}
      <div>
        <div className="font-mono text-lg font-bold text-text-primary">
          {candidate.ticker}
        </div>
        <div className="text-xs text-text-secondary truncate">
          {candidate.name}
        </div>
      </div>

      {/* Composite score */}
      <div className="font-mono text-3xl text-accent">
        {candidate.score}
      </div>

      {/* Factor bars */}
      <div className="space-y-2">
        <FactorBar label="Quality" value={candidate.quality_percentile} />
        <FactorBar label="Value" value={candidate.value_percentile} />
        <FactorBar label="Momentum" value={candidate.momentum_percentile} />
      </div>

      {/* Sector + timestamp */}
      <div className="flex items-center gap-2 mt-auto pt-2">
        <span className="text-[10px] font-mono uppercase tracking-wider bg-bg-subtle text-text-tertiary px-2 py-0.5 rounded">
          {candidate.sector}
        </span>
        <span className="text-[10px] text-text-tertiary">
          scored {timeAgo(candidate.scored_at)}
        </span>
      </div>
    </div>
  )
}

export function ResultsShowcaseSection({ data }: ResultsShowcaseSectionProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!panelRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = panelRef.current
      if (!el) return

      gsap.set(el, { opacity: 0, y: 24 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" })
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
      <section id="results" className="py-20 px-6">
        <div className="max-w-5xl mx-auto text-center text-text-secondary text-sm">
          Scoring data loads after the engine completes a cycle.
        </div>
      </section>
    )
  }

  // Empty candidates — cycle in progress
  if (data.candidates.length === 0) {
    return (
      <section id="results" className="py-20 px-6">
        <div className="max-w-5xl mx-auto text-center text-text-secondary text-sm">
          Scoring in progress — results appear after each cycle.
        </div>
      </section>
    )
  }

  const top3 = data.candidates.slice(0, 3)
  const eliminated = data.total_scored - data.surviving_count
  const lastCycle = timeAgo(data.last_updated)

  return (
    <section id="results" className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div
          ref={panelRef}
          className="border border-border-subtle rounded-xl overflow-hidden"
          style={{ background: "var(--color-bg-elevated)" }}
        >
          {/* Terminal-style header */}
          <div
            className="px-6 py-3 border-b border-border-subtle"
            style={{ background: "var(--color-bg-subtle)" }}
          >
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary">
              Current Cycle Results
            </span>
          </div>

          {/* 3-column candidate grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
            {top3.map((candidate) => (
              <CandidateColumn key={candidate.ticker} candidate={candidate} />
            ))}
          </div>

          {/* Footer stats line */}
          <div className="px-6 py-3 border-t border-border-subtle font-mono text-xs text-text-tertiary text-center">
            {data.total_scored.toLocaleString("en-US")} stocks scored
            {" · "}
            {eliminated.toLocaleString("en-US")} eliminated
            {" · "}
            {data.surviving_count.toLocaleString("en-US")} survived
            {" · "}
            Last cycle: {lastCycle}
          </div>
        </div>
      </div>
    </section>
  )
}
