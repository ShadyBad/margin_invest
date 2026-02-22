"use client"

import { useEffect, useRef } from "react"

const notForItems = ["Narrative traders", "Signal chasers", "Emotion-driven decisions"]
const forItems = ["Long-horizon allocators", "Portfolio operators", "Structured decision-makers"]

export function PositioningSection() {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!gridRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = gridRef.current
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
    <section id="positioning" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary text-center mb-16">
          Built for disciplined capital allocators.
        </h2>
        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16"
        >
          {/* Not for column */}
          <div className="text-center md:border-r md:border-border-subtle md:pr-12">
            <div className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-6">
              Not for
            </div>
            <ul className="space-y-3">
              {notForItems.map((item) => (
                <li key={item} className="text-sm text-text-tertiary">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          {/* For column */}
          <div className="text-center">
            <div className="text-xs uppercase tracking-[0.2em] text-accent mb-6">
              For
            </div>
            <ul className="space-y-3">
              {forItems.map((item) => (
                <li key={item} className="text-sm text-accent">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
