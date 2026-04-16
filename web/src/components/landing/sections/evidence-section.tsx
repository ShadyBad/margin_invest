"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { SelectivityFunnel } from "../visualizations/selectivity-funnel"
import { SectorBarChart } from "../visualizations/sector-bar-chart"
import { FactorDensityCurves } from "../visualizations/factor-density-curves"
import { ProofHeatmap } from "../proof-heatmap"
import type { CandidateCard } from "../shared/types"

interface EvidenceSectionProps {
  candidates?: CandidateCard[]
  totalUniverse?: number
  eligibleCount?: number
  totalScored?: number
  survivingCount?: number
}

export function EvidenceSection({
  candidates = [],
  totalUniverse = 0,
  eligibleCount = 0,
  totalScored = 0,
  survivingCount = 0,
}: EvidenceSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

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
      const el = sectionRef.current
      if (!el) return

      // Funnel block
      const funnelBlock = el.querySelector("[data-funnel-block]")
      if (funnelBlock) {
        gsap.set(funnelBlock, { opacity: 0, y: 24, filter: "blur(6px)" })
        const st = ScrollTrigger.create({ trigger: funnelBlock, start: "top 88%", once: true,
          onEnter: () => { gsap.to(funnelBlock, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, ease: "power2.out" }) },
        })
        cleanups.push(() => st.kill())
      }

      // Forensic cards
      const cards = el.querySelectorAll("[data-forensic-card]")
      if (cards.length > 0) {
        gsap.set(cards, { opacity: 0, y: 24, filter: "blur(6px)" })
        const st = ScrollTrigger.create({ trigger: cards[0], start: "top 88%", once: true,
          onEnter: () => { gsap.to(cards, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, stagger: 0.1, ease: "power2.out" }) },
        })
        cleanups.push(() => st.kill())
      }
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  return (
    <section id="evidence" ref={sectionRef} className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Block A: THE SELECTION FUNNEL */}
        <div data-funnel-block className="mb-20">
          <h2 className="text-headline-md uppercase mb-10" style={{ color: "var(--color-on-surface)" }}>
            The Selection Funnel
          </h2>
          <div className="p-8 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
            <SelectivityFunnel universeCount={totalUniverse} eligibleCount={eligibleCount} scoredCount={totalScored} survivingCount={survivingCount} />
          </div>
          <p className="text-label-md mt-6 text-center" style={{ color: "var(--color-on-surface-variant)" }}>
            {totalUniverse.toLocaleString()} &rarr; {eligibleCount.toLocaleString()} &rarr; {totalScored.toLocaleString()} &rarr; {survivingCount.toLocaleString()}
          </p>
        </div>

        {/* Block B: FORENSIC ANALYSIS */}
        <div>
          <h2 className="text-headline-md uppercase mb-10" style={{ color: "var(--color-on-surface)" }}>
            Forensic Analysis
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:items-stretch">
            {/* Left: Sector Breakdown + Factor Distributions stacked */}
            <div className="flex flex-col gap-6 min-w-0">
              <div data-forensic-card className="p-6 rounded-lg flex-1" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
                <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>SECTOR BREAKDOWN</div>
                <SectorBarChart candidates={candidates} />
              </div>
              <div data-forensic-card className="p-6 rounded-lg flex-1" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
                <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>FACTOR DISTRIBUTIONS</div>
                <FactorDensityCurves candidates={candidates} />
              </div>
            </div>

            {/* Right: Factor Correlation — stretches to match left height */}
            <div data-forensic-card className="p-6 rounded-lg flex flex-col min-w-0 h-full" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>FACTOR CORRELATION</div>
              <div className="flex-1 flex items-center justify-center">
                <ProofHeatmap candidates={candidates} />
              </div>
            </div>
          </div>
          <div className="mt-8 text-center">
            <Link href="/methodology" className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>
              Structure replaces intuition with evidence.{" "}
              <span style={{ color: "var(--color-primary)" }}>See full methodology &rarr;</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
