"use client"

import { useEffect, useRef } from "react"

const PROBLEM_BULLETS = [
  "No filtering discipline",
  "No factor weighting memory",
  "No sector normalization",
  "No portfolio-level correlation awareness",
]

export function ProblemSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    let triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default

      gsap.registerPlugin(ScrollTrigger)

      const section = sectionRef.current
      if (!section) return

      const headline = section.querySelector("[data-problem-headline]")
      const bullets = section.querySelectorAll("[data-problem-bullet]")

      if (headline) {
        gsap.set(headline, { opacity: 0, y: 20 })
        const trigger = ScrollTrigger.create({
          trigger: section,
          start: "top 80%",
          onEnter: () => {
            gsap.to(headline, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" })
          },
          once: true,
        })
        triggers.push(trigger)
      }

      if (bullets.length) {
        gsap.set(bullets, { opacity: 0, y: 12 })
        const trigger = ScrollTrigger.create({
          trigger: section,
          start: "top 70%",
          onEnter: () => {
            bullets.forEach((bullet, i) => {
              gsap.to(bullet, {
                opacity: 1,
                y: 0,
                duration: 0.5,
                delay: i * 0.1,
                ease: "power2.out",
              })
            })
          },
          once: true,
        })
        triggers.push(trigger)
      }
    }

    animate().catch(() => {
      // Silently handle module resolution failures during test teardown
    })

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  return (
    <section
      id="problem"
      ref={sectionRef}
      className="pt-[120px] pb-20 px-6 border-b border-border-subtle"
    >
      <div className="max-w-3xl mx-auto">
        <h2
          data-problem-headline
          className="font-display text-4xl md:text-[36px] leading-tight tracking-tight text-text-primary mb-10"
        >
          Most investors react. Few operate with structure.
        </h2>

        <ul className="space-y-4">
          {PROBLEM_BULLETS.map((bullet) => (
            <li
              key={bullet}
              data-problem-bullet
              className="text-lg text-text-secondary flex items-start gap-3"
            >
              <span className="text-text-tertiary shrink-0" aria-hidden="true">
                &mdash;
              </span>
              {bullet}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
