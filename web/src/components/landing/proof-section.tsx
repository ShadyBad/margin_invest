"use client"

import { useEffect, useRef, type ReactNode } from "react"
import { MicroMetadata } from "./micro-metadata"
import { ProofFactorBars } from "./proof-factor-bars"
import { ProofSelectivityFunnel } from "./proof-selectivity-funnel"
import { ProofSectorChart } from "./proof-sector-chart"
import { ProofHeatmap } from "./proof-heatmap"
import { ProofHistoricalChart } from "./proof-historical-chart"
import type { CandidateCard } from "./types"

interface ProofCardProps {
  title: string
  children: ReactNode
}

function ProofCard({ title, children }: ProofCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!cardRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = cardRef.current
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

  return (
    <div ref={cardRef} className="terminal-card p-6">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
        {title}
      </div>
      {children}
    </div>
  )
}

interface ProofSectionProps {
  candidates?: CandidateCard[]
}

export function ProofSection({ candidates = [] }: ProofSectionProps) {
  return (
    <section id="proof" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary text-center mb-4">
          Structure replaces intuition with evidence.
        </h2>
        <div className="text-center mb-16">
          <MicroMetadata text="Sector-neutral by design" />
        </div>
        <div className="text-center mb-8 space-y-2">
          <p className="text-sm font-mono text-text-primary">
            Every signal recorded · Sector-neutral · Live tracking from day one
          </p>
          <p className="text-[10px] text-text-tertiary max-w-md mx-auto">
            Past performance does not guarantee future results. Walk-forward backtesting with
            point-in-time data and transaction costs is in development. Full methodology on
            the backtesting page.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProofCard title="Factor Transparency">
            <ProofFactorBars />
          </ProofCard>
          <ProofCard title="System Selectivity">
            <ProofSelectivityFunnel />
          </ProofCard>
          <ProofCard title="Sector Breakdown">
            <ProofSectorChart candidates={candidates} />
          </ProofCard>
          <ProofCard title="Correlation Heatmap">
            <ProofHeatmap />
          </ProofCard>
          <ProofCard title="Historical Application">
            <ProofHistoricalChart />
          </ProofCard>
        </div>
      </div>
    </section>
  )
}
