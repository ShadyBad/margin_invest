"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"
import { HeroSearch } from "./hero-search"

interface HeroSectionProps {
  data: HomepageData | null
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- data reserved for future server-side injection
export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false

    async function animate() {
      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default

      const section = sectionRef.current
      if (!section) return

      const headline = section.querySelector("[data-hero-headline]")
      const subtext = section.querySelector("[data-hero-subtext]")
      const search = section.querySelector("[data-hero-ctas]")

      const textTargets = [headline, subtext, search].filter(Boolean)
      gsap.set(textTargets, { opacity: 0, y: 20 })

      textTargets.forEach((target, i) => {
        gsap.to(target, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          delay: i * 0.12,
          ease: "power2.out",
        })
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative flex items-center justify-center overflow-hidden"
      style={{
        minHeight: "100svh",
        background:
          "radial-gradient(ellipse 60% 50% at 50% 30%, rgba(26,122,90,0.10) 0%, transparent 65%), var(--color-bg-primary)",
      }}
    >
      {/* Noise texture overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: "url('/noise.svg')",
          backgroundRepeat: "repeat",
          opacity: 0.4,
        }}
      />

      {/* Grid overlay for depth */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-grid-line) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 1,
        }}
      />

      <div className="max-w-3xl w-full text-center pt-16 py-24 px-6 relative z-10">
        <h1
          data-hero-headline
          className="font-display leading-[1.05] tracking-tight mb-6"
          style={{ fontSize: "clamp(48px, 7vw, 72px)" }}
        >
          <span className="block text-text-primary">Discipline.</span>
          <span className="block" style={{ color: "var(--color-accent)" }}>
            Engineered.
          </span>
        </h1>

        <p
          data-hero-subtext
          className="text-lg md:text-xl text-text-secondary max-w-xl mx-auto mb-10 leading-relaxed"
        >
          A deterministic scoring engine for 3,056 US equities. No opinions. No
          overrides. Search one.
        </p>

        <HeroSearch />
      </div>

      {/* Bottom fade gradient */}
      <div
        className="pointer-events-none absolute bottom-0 left-0 right-0 h-32"
        style={{
          background:
            "linear-gradient(to bottom, transparent, var(--color-bg-primary))",
        }}
      />
    </section>
  )
}
