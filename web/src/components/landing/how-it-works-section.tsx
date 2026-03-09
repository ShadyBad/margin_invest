"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"

interface HowItWorksSectionProps {
  data: HomepageData | null
}

interface PipelineStep {
  number: string
  label: string
  getValue: (data: HomepageData) => number
  description: string
}

const STEPS: PipelineStep[] = [
  {
    number: "01",
    label: "SCAN",
    getValue: (d) => d.total_universe,
    description: "Ingest the full US equity universe from SEC filings and market feeds.",
  },
  {
    number: "02",
    label: "ELIMINATE",
    getValue: (d) => d.eligible_count,
    description: "Fail-fast filters remove penny stocks, delistings, and illiquid names.",
  },
  {
    number: "03",
    label: "SCORE",
    getValue: (d) => d.total_scored,
    description: "Five-factor percentile ranking within GICS sector peers.",
  },
  {
    number: "04",
    label: "SURFACE",
    getValue: (d) => d.surviving_count,
    description: "Only the highest-conviction positions survive to your screen.",
  },
]

function formatCount(n: number): string {
  return n.toLocaleString("en-US")
}

function ArrowIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-text-tertiary opacity-40"
    >
      <path d="M5 12h14" />
      <path d="M12 5l7 7-7 7" />
    </svg>
  )
}

export function HowItWorksSection({ data }: HowItWorksSectionProps) {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!gridRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = gridRef.current
      if (!el) return

      // Select only the step cards (not the arrow separators)
      const cards = el.querySelectorAll<HTMLElement>("[data-step-card]")
      cards.forEach((card) => gsap.set(card, { opacity: 0, y: 20 }))

      const trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          cards.forEach((card, i) => {
            gsap.to(card, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              delay: i * 0.12,
              ease: "power2.out",
            })
          })
        },
      })
      triggers.push(trigger)
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  return (
    <section id="how-it-works" className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        {/* Section header */}
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-10 flex items-center gap-2 justify-center">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50" />
          HOW THE ENGINE WORKS
        </div>

        {/* Pipeline grid */}
        <div
          ref={gridRef}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] gap-y-4 sm:gap-y-6 items-stretch"
        >
          {STEPS.map((step, i) => (
            <div key={step.number} className="contents">
              {/* Step card */}
              <div
                data-step-card
                className="bg-bg-elevated border border-border-subtle rounded-xl p-5 flex flex-col"
              >
                {/* Step number */}
                <div className="font-mono text-xs text-accent/60 mb-2">
                  {step.number}
                </div>

                {/* Label */}
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-3">
                  {step.label}
                </div>

                {/* Live count */}
                <div className="font-mono text-3xl text-text-primary mb-3">
                  {data ? formatCount(step.getValue(data)) : "—"}
                </div>

                {/* Description */}
                <p className="text-xs text-text-secondary leading-relaxed mt-auto">
                  {step.description}
                </p>
              </div>

              {/* Arrow between steps (desktop only) */}
              {i < STEPS.length - 1 && (
                <div className="hidden lg:flex items-center justify-center px-2">
                  <ArrowIcon />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
