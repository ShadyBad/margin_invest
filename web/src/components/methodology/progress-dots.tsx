"use client"

import { useEffect, useState } from "react"

const STAGES = [
  { id: "pipeline", label: "Pipeline" },
  { id: "universe", label: "Universe" },
  { id: "filters", label: "Filters" },
  { id: "scoring", label: "Scoring" },
  { id: "conviction", label: "Conviction" },
  { id: "ml", label: "ML" },
  { id: "output", label: "Output" },
]

export function MethodologyProgressDots() {
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const sections = STAGES.map((s) =>
      document.querySelector(`[data-methodology-section="${s.id}"]`)
    ).filter(Boolean) as HTMLElement[]

    if (sections.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = sections.indexOf(entry.target as HTMLElement)
            if (idx !== -1) setActiveIndex(idx)
          }
        }
      },
      { rootMargin: "-40% 0px -40% 0px", threshold: 0 }
    )

    for (const section of sections) observer.observe(section)
    return () => observer.disconnect()
  }, [])

  return (
    <nav
      className="fixed right-4 top-1/2 -translate-y-1/2 z-30 hidden lg:flex flex-col items-center gap-3"
      aria-label="Methodology progress"
    >
      {STAGES.map((stage, i) => (
        <button
          key={stage.id}
          onClick={() => {
            const el = document.querySelector(
              `[data-methodology-section="${stage.id}"]`
            )
            el?.scrollIntoView({ behavior: "smooth", block: "start" })
          }}
          className="group relative flex items-center"
          aria-label={stage.label}
          aria-current={i === activeIndex ? "step" : undefined}
        >
          <span
            className={`block w-2 h-2 rounded-full transition-all duration-300 ${
              i === activeIndex
                ? "bg-accent scale-125"
                : i < activeIndex
                  ? "bg-accent/40"
                  : "bg-white/15"
            }`}
          />
          <span className="absolute right-5 whitespace-nowrap text-[11px] text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
            {stage.label}
          </span>
        </button>
      ))}
    </nav>
  )
}
