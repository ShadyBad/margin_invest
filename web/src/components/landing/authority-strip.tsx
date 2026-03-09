"use client"

import { useEffect, useRef } from "react"

const FACTS = ["SEC EDGAR filings", "11 GICS sectors", "Scored daily"]

export function AuthorityStrip() {
  const sectionRef = useRef<HTMLElement>(null)
  const factRefs = useRef<(HTMLSpanElement | null)[]>([])

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const scrollTriggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const [left, center, right] = factRefs.current
      if (!left || !center || !right) return

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: el,
          start: "top 80%",
          end: "top 40%",
          scrub: true,
        },
      })

      tl.fromTo(left, { x: -30, opacity: 0 }, { x: 0, opacity: 1 }, 0)
      tl.fromTo(center, { y: 12, opacity: 0 }, { y: 0, opacity: 1 }, 0.05)
      tl.fromTo(right, { x: 30, opacity: 0 }, { x: 0, opacity: 1 }, 0.1)

      const st = tl.scrollTrigger
      if (st) scrollTriggers.push(st as unknown as { kill: () => void })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      scrollTriggers.forEach((st) => st.kill())
    }
  }, [])

  return (
    <section ref={sectionRef} className="relative" style={{ minHeight: "50vh" }}>
      <div
        className="max-w-4xl mx-auto px-6 flex items-center justify-center"
        style={{ minHeight: "50vh" }}
      >
        <div className="w-full">
          {/* Horizontal rule */}
          <div className="border-t border-border-subtle" />

          {/* Three data points centered on the rule */}
          <div className="flex items-center justify-between -mt-3 px-4">
            {FACTS.map((fact, i) => (
              <span
                key={fact}
                ref={(el) => {
                  factRefs.current[i] = el
                }}
                className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary bg-bg-primary px-3"
                style={{ opacity: 0 }}
              >
                {fact}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
