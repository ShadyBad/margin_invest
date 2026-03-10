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

      // Panel border/container fades in
      gsap.set(el, { opacity: 0 })

      // Content items stagger in
      const items = el.querySelectorAll("[data-evidence-item]")
      if (items.length > 0) {
        gsap.set(items, { opacity: 0, y: 16 })
      }

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, duration: 0.5, ease: "power2.out" })
          if (items.length > 0) {
            gsap.to(items, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              stagger: 0.1,
              delay: 0.15,
              ease: "power2.out",
            })
          }
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
    <section id="evidence" className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div
          ref={panelRef}
          className="border border-border-subtle rounded-xl overflow-hidden"
          style={{ background: "var(--color-bg-elevated)" }}
        >
          {/* Monospace header strip */}
          <div
            className="px-6 py-3 border-b border-border-subtle flex items-center gap-2"
            style={{ background: "var(--color-bg-subtle)" }}
          >
            <span
              className="inline-block w-2 h-2 rounded-full bg-accent animate-pulse"
              aria-hidden="true"
            />
            <span
              className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary"
              data-testid="evidence-header"
            >
              System Output — Cycle Results
            </span>
          </div>

          {/* Row 1: stacked funnel+sector on left, correlation on right */}
          <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border-subtle">
            {/* Left: Funnel + Sector stacked — each vertically centered in its half */}
            <div className="divide-y divide-border-subtle flex flex-col">
              <div className="p-6 flex-1 flex flex-col justify-center" data-evidence-item>
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                  Selectivity Funnel
                </div>
                <SelectivityFunnel
                  universeCount={totalUniverse}
                  eligibleCount={eligibleCount}
                  scoredCount={totalScored}
                  survivingCount={survivingCount}
                />
              </div>

              <div className="p-6 flex-1 flex flex-col justify-center" data-evidence-item>
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                  Sector Breakdown
                </div>
                <SectorBarChart candidates={candidates} />
              </div>
            </div>

            {/* Right: Factor Correlation */}
            <div className="p-6" data-evidence-item>
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Factor Correlation
              </div>
              <ProofHeatmap />
            </div>
          </div>

          {/* Row 2: Full-width factor density curves */}
          <div className="px-6 py-5 border-t border-border-subtle" data-evidence-item>
            <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
              Factor Distribution — All Candidates
            </div>
            <FactorDensityCurves candidates={candidates} />
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-border-subtle text-center">
            <Link
              href="/methodology"
              className="text-sm text-text-secondary hover:text-accent transition-colors"
            >
              Structure replaces intuition with evidence.{" "}
              <span className="text-accent">See full methodology &rarr;</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
