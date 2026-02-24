"use client"

import { useEffect, useRef } from "react"

interface EliminationVignetteProps {
  eliminatedPct?: number
}

export function EliminationVignette({ eliminatedPct }: EliminationVignetteProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      gsap.set(el.querySelectorAll("[data-vignette]"), { opacity: 0, y: 16 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 80%",
        once: true,
        onEnter: () => {
          gsap.to(el.querySelectorAll("[data-vignette]"), {
            opacity: 1,
            y: 0,
            duration: 0.5,
            stagger: 0.1,
            ease: "power2.out",
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  const pct = eliminatedPct ?? 70

  return (
    <section ref={sectionRef} className="py-16 px-6">
      <div className="max-w-3xl mx-auto text-center space-y-4">
        <p data-vignette className="font-mono text-4xl md:text-5xl text-accent font-semibold">
          {pct}%
        </p>
        <p data-vignette className="text-lg text-text-primary">
          of US equities are eliminated before scoring begins.
        </p>
        <p data-vignette className="text-sm text-text-secondary max-w-xl mx-auto">
          Six forensic filters — including earnings manipulation detection and bankruptcy
          probability screening — remove financially fragile companies from the universe.
          What survives is scored. Everything else is rejected.
        </p>
      </div>
    </section>
  )
}
