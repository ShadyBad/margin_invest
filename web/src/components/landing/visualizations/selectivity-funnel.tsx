"use client"

import { useEffect, useRef, useState } from "react"

/**
 * SelectivityFunnel — Vertical funnel showing the filtering pipeline.
 *
 * Renders 4 horizontal bars of decreasing width showing how equities
 * are narrowed down at each stage: Universe -> Eligible -> Scored -> Surviving.
 * Each stage animates in with a countdown (1.5s total) and includes filter descriptions.
 */

interface SelectivityFunnelProps {
  universeCount: number
  eligibleCount: number
  scoredCount: number
  survivingCount: number
}

const STAGES = [
  { key: "universe", label: "Universe Screened", description: "Penny stocks removed", propKey: "universeCount" },
  { key: "eligible", label: "Passed Filters", description: "Altman Z-Score filter", propKey: "eligibleCount" },
  { key: "scored", label: "Scored", description: "Beneish M-Score calculated", propKey: "scoredCount" },
  { key: "surviving", label: "Surviving Candidates", description: "Final analysis ready", propKey: "survivingCount" },
] as const

/** Map stage index to progressively more intense accent opacity */
const STAGE_COLORS = [
  "rgba(26,122,90,0.15)", // universe — subtle
  "rgba(26,122,90,0.30)", // eligible
  "rgba(26,122,90,0.55)", // scored
  "rgba(26,122,90,0.85)", // surviving — strongest
]

export function SelectivityFunnel({
  universeCount,
  eligibleCount,
  scoredCount,
  survivingCount,
}: SelectivityFunnelProps) {
  const counts: Record<string, number> = {
    universeCount,
    eligibleCount,
    scoredCount,
    survivingCount,
  }

  const max = universeCount || 1
  const containerRef = useRef<HTMLDivElement>(null)
  const [animatedStages, setAnimatedStages] = useState<Set<string>>(new Set())

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReducedMotion) {
      // Show all stages immediately without animation
      setAnimatedStages(new Set(STAGES.map((s) => s.key)))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Stagger each stage animation by ~375ms (1500ms / 4 stages)
            STAGES.forEach((stage, idx) => {
              setTimeout(() => {
                setAnimatedStages((prev) => new Set(prev).add(stage.key))
              }, idx * 375)
            })
            observer.unobserve(container)
          }
        })
      },
      { threshold: 0.2 }
    )

    observer.observe(container)
    return () => observer.unobserve(container)
  }, [])

  return (
    <div
      ref={containerRef}
      className="flex flex-col gap-3"
      aria-label="Selectivity funnel showing how equities are filtered at each stage"
    >
      {STAGES.map((stage, i) => {
        const count = counts[stage.propKey]
        const widthPct = Math.max(6, (count / max) * 100)
        const isAnimated = animatedStages.has(stage.key)

        return (
          <div key={stage.key} data-testid={`funnel-stage-${stage.key}`} className="group/funnel cursor-default">
            <div className="flex items-center justify-between mb-0.5">
              <div className="flex-1">
                <span className="text-mono-label text-text-tertiary transition-colors duration-200 group-hover/funnel:text-text-secondary">{stage.label}</span>
                <p className="text-xs text-text-tertiary mt-0.5">{stage.description}</p>
              </div>
              <span className="font-mono text-xs text-text-secondary tabular-nums transition-colors duration-200 group-hover/funnel:text-text-primary ml-4">
                {count.toLocaleString()}
              </span>
            </div>
            <div
              className={`h-7 rounded-sm transition-all duration-500 group-hover/funnel:brightness-125 group-hover/funnel:shadow-[0_0_8px_rgba(26,122,90,0.2)] ${
                isAnimated ? "opacity-100" : "opacity-0"
              }`}
              data-testid={`funnel-bar-${stage.key}`}
              style={{
                width: isAnimated ? `${widthPct}%` : "0%",
                backgroundColor: STAGE_COLORS[i],
              }}
            />
          </div>
        )
      })}
    </div>
  )
}
