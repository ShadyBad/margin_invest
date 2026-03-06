"use client"

import Link from "next/link"
import { useEffect, useRef } from "react"

export function TestimonialSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      gsap.set(el.querySelectorAll("[data-cta-animate]"), { opacity: 0, y: 16 })

      ScrollTrigger.create({
        trigger: el,
        start: "top 80%",
        once: true,
        onEnter: () => {
          gsap.to(el.querySelectorAll("[data-cta-animate]"), {
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
    }
  }, [])

  return (
    <section ref={sectionRef} className="py-24 px-6">
      <div
        className="relative mx-auto text-center overflow-hidden"
        style={{
          maxWidth: "640px",
          padding: "48px 32px",
          background: "var(--color-accent-warm-muted)",
          border: "1px solid rgba(201, 150, 59, 0.20)",
          borderRadius: "16px",
        }}
      >
        {/* Top accent line */}
        <div
          className="absolute top-0 left-0 right-0"
          style={{
            height: "2px",
            background:
              "linear-gradient(90deg, transparent, var(--color-accent-warm), transparent)",
            borderRadius: "16px 16px 0 0",
          }}
        />

        <h2
          data-cta-animate
          className="font-display text-3xl md:text-4xl text-text-primary mb-4"
        >
          Join the first cohort.
        </h2>
        <p
          data-cta-animate
          className="text-base text-text-secondary mb-8 max-w-md mx-auto"
        >
          Margin Invest is in early access. Be one of the first to operate with
          structure.
        </p>
        <div data-cta-animate>
          <Link
            href="/onboarding"
            className="inline-block text-sm font-medium rounded-lg px-8 py-3 transition-colors"
            style={{
              background: "var(--color-accent)",
              color: "var(--color-bg-primary)",
            }}
          >
            Request Early Access
          </Link>
        </div>
      </div>
    </section>
  )
}
