"use client"

import { useCallback, useEffect, useRef, useState } from "react"

/**
 * SelectivityFunnel — Vertical funnel showing the filtering pipeline.
 *
 * Renders 4 horizontal bars of decreasing width showing how equities
 * are narrowed down at each stage: Universe -> Eligible -> Scored -> Surviving.
 * Each stage animates in with a counting number + bar grow (~1.5s total).
 * Final stage pulses on completion.
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
  "var(--color-surface-container)",
  "var(--color-surface-container-high)",
  "var(--color-surface-container-highest)",
  "var(--color-primary-container)",
]

const STAGGER_MS = 375 // per stage
const COUNT_DURATION_MS = 350 // how long the number counts up
const COUNT_FRAMES = 20 // steps in the counting animation

/**
 * Hook: animates a number from 0 to `target` over `duration` ms.
 * Only starts when `active` flips to true.
 */
function useCountUp(target: number, active: boolean, duration: number = COUNT_DURATION_MS): number {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (!active) {
      setDisplay(0)
      return
    }

    let frame = 0
    const step = duration / COUNT_FRAMES
    const interval = setInterval(() => {
      frame++
      if (frame >= COUNT_FRAMES) {
        setDisplay(target)
        clearInterval(interval)
      } else {
        // Ease-out curve: fast start, slow finish
        const progress = 1 - Math.pow(1 - frame / COUNT_FRAMES, 2)
        setDisplay(Math.round(target * progress))
      }
    }, step)

    return () => clearInterval(interval)
  }, [active, target, duration])

  return active ? display : 0
}

function FunnelStage({
  stage,
  index,
  count,
  maxCount,
  isAnimated,
  isFinal,
  allDone,
}: {
  stage: (typeof STAGES)[number]
  index: number
  count: number
  maxCount: number
  isAnimated: boolean
  isFinal: boolean
  allDone: boolean
}) {
  const widthPct = Math.max(6, (count / maxCount) * 100)
  const displayCount = useCountUp(count, isAnimated)

  return (
    <div data-testid={`funnel-stage-${stage.key}`} className="group/funnel cursor-default">
      <div className="flex items-center justify-between mb-0.5">
        <div className="flex-1">
          <span className="text-label-sm transition-colors duration-200" style={{ color: "var(--color-on-surface-variant)" }}>
            {stage.label}
          </span>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{stage.description}</p>
        </div>
        <span
          className="text-label-md tabular-nums transition-colors duration-200 ml-4"
          style={{
            color: isFinal && allDone ? "var(--color-primary)" : "var(--color-on-surface-variant)",
            fontWeight: isFinal && allDone ? 700 : 400,
          }}
        >
          {isAnimated ? displayCount.toLocaleString() : "\u2014"}
        </span>
      </div>
      <div
        className={`h-7 rounded-sm transition-all duration-500 group-hover/funnel:brightness-125 group-hover/funnel:shadow-[0_0_8px_rgba(26,122,90,0.2)] ${
          isAnimated ? "opacity-100" : "opacity-0"
        }`}
        data-testid={`funnel-bar-${stage.key}`}
        style={{
          width: isAnimated ? `${widthPct}%` : "0%",
          backgroundColor: STAGE_COLORS[index],
        }}
      />
    </div>
  )
}

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
  const [allDone, setAllDone] = useState(false)

  const triggerSequence = useCallback(() => {
    STAGES.forEach((stage, idx) => {
      setTimeout(() => {
        setAnimatedStages((prev) => new Set(prev).add(stage.key))
        // Mark all done after last stage finishes counting
        if (idx === STAGES.length - 1) {
          setTimeout(() => setAllDone(true), COUNT_DURATION_MS)
        }
      }, idx * STAGGER_MS)
    })
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReducedMotion) {
      setAnimatedStages(new Set(STAGES.map((s) => s.key)))
      setAllDone(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            triggerSequence()
            observer.unobserve(container)
          }
        })
      },
      { threshold: 0.2 }
    )

    observer.observe(container)
    return () => observer.unobserve(container)
  }, [triggerSequence])

  return (
    <div
      ref={containerRef}
      className="flex flex-col gap-3"
      aria-label="Selectivity funnel showing how equities are filtered at each stage"
    >
      {STAGES.map((stage, i) => (
        <FunnelStage
          key={stage.key}
          stage={stage}
          index={i}
          count={counts[stage.propKey]}
          maxCount={max}
          isAnimated={animatedStages.has(stage.key)}
          isFinal={i === STAGES.length - 1}
          allDone={allDone}
        />
      ))}
    </div>
  )
}
