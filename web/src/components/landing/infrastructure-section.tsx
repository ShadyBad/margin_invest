"use client"

import { useEffect, useRef } from "react"

const bullets = [
  "SEC Filings + Earnings Transcripts",
  "Market Data Feeds (Daily Refresh)",
  "Encrypted API Key Storage",
  "Deterministic, Audit-Friendly Scoring",
  "No Hidden Heuristics",
]

export function InfrastructureSection() {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!gridRef.current) return

    let cancelled = false
    let triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = gridRef.current
      if (!el) return

      const children = Array.from(el.children) as HTMLElement[]
      children.forEach((child) => gsap.set(child, { opacity: 0, y: 16 }))

      const trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          children.forEach((child, i) => {
            gsap.to(child, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              delay: i * 0.1,
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
    <section id="infrastructure" className="py-[100px] px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary text-center mb-4">
          Institutional-Grade Infrastructure
        </h2>
        <p className="text-text-secondary text-center mb-16">
          Built on verified public data and deterministic scoring architecture.
        </p>
        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-3 gap-y-0 gap-x-12"
        >
          {bullets.map((bullet) => (
            <div
              key={bullet}
              className="text-sm text-text-secondary py-4 border-b border-border-subtle"
            >
              <span className="mr-2">&mdash;</span>
              {bullet}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
