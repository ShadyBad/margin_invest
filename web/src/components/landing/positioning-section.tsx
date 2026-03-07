"use client"

import { useEffect, useRef } from "react"

const notForItems = [
  "Narrative-driven conviction",
  "Signal chasers and day traders",
  "Anyone who needs an override button",
]
const forItems = [
  "Investors who know their process is broken",
  "People who want math, not opinions",
  "Anyone willing to trust structure over stories",
]

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
    <section id="positioning" className="py-16 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary text-center mb-16">
          The system has no opinion. That&apos;s the point.
        </h2>
        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16"
        >
          {/* Not for column */}
          <div className="md:border-r md:border-border-subtle md:pr-12">
            <div className="text-[11px] uppercase tracking-[0.25em] text-text-tertiary mb-6">
              Not for
            </div>
            <ul>
              {notForItems.map((item, i) => (
                <li
                  key={item}
                  className={`flex items-start gap-3 py-6 text-sm text-text-tertiary${i < notForItems.length - 1 ? ' border-b border-border-subtle' : ''}`}
                >
                  <span className="text-text-tertiary shrink-0" aria-hidden="true">&mdash;</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
          {/* For column */}
          <div style={{ background: 'rgba(26,122,90,0.03)', borderRadius: '12px', padding: '24px' }}>
            <div className="text-[11px] uppercase tracking-[0.25em] text-accent mb-6">
              For
            </div>
            <ul>
              {forItems.map((item, i) => (
                <li
                  key={item}
                  className={`flex items-start gap-3 py-6 text-sm text-text-primary${i < forItems.length - 1 ? ' border-b border-border-subtle' : ''}`}
                >
                  <span className="text-accent shrink-0" aria-hidden="true">✓</span>
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
