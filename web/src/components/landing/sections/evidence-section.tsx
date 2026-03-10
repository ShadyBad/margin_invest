"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { ProofSelectivityFunnel } from "../proof-selectivity-funnel"
import { ProofSectorChart } from "../proof-sector-chart"
import { ProofHeatmap } from "../proof-heatmap"
import type { CandidateCard } from "../shared/types"

interface EvidenceSectionProps {
  candidates?: CandidateCard[]
}

export function EvidenceSection({ candidates = [] }: EvidenceSectionProps) {
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

  return (
    <section id="evidence" className="py-20 px-6">
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
              System Output — Current Scoring Cycle
            </span>
          </div>

          {/* 3-column content */}
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Selectivity Funnel
              </div>
              <ProofSelectivityFunnel />
            </div>
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Sector Breakdown
              </div>
              <ProofSectorChart candidates={candidates} />
            </div>
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Factor Correlation
              </div>
              <ProofHeatmap />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-border-subtle text-center">
            <Link
              href="/methodology"
              className="text-sm text-text-secondary hover:text-accent transition-colors"
            >
              Structure replaces intuition with evidence.{" "}
              <span className="text-accent">See full methodology →</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
