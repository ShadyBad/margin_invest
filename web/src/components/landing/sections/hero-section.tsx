"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import type { HomepageData } from "../shared/types"
import { HeroSearch } from "../hero-search"
import { InstrumentPanel } from "./instrument-panel"

interface HeroSectionProps {
  data: HomepageData | null
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false

    async function animate() {
      // Respect prefers-reduced-motion — skip entrance animations
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default

      const section = sectionRef.current
      if (!section) return

      // Left column: sequential text fade-in
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

      // Right column: card scale + rotation entrance
      const card = section.querySelector("[data-hero-card]")
      if (card) {
        gsap.set(card, { opacity: 0, scale: 0.95, rotation: -2 })
        gsap.to(card, {
          opacity: 1,
          scale: 1,
          rotation: 0,
          duration: 0.8,
          delay: 0.3,
          ease: "power2.out",
        })
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
    }
  }, [])

  const topCandidate = data?.candidates?.[0] ?? null

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative flex items-center justify-center overflow-x-clip"
      style={{
        minHeight: "80svh",
        background:
          "radial-gradient(ellipse 70% 55% at 50% 30%, rgba(26,122,90,0.18) 0%, transparent 60%), var(--color-bg-primary)",
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

      {/* Grid overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-grid-line) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />

      {/* Two-column editorial layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[55%_45%] gap-10 lg:gap-6 max-w-7xl w-full items-center pt-16 py-24 px-6 relative z-10">
        {/* Left column — headline + search */}
        <div className="flex flex-col justify-center">
          <h1
            data-hero-headline
            className="text-display-1 tracking-tight mb-6"
          >
            <span className="block text-text-primary">Discipline.</span>
            <span className="block" style={{ color: "var(--color-accent)" }}>
              Engineered.
            </span>
          </h1>

          <p
            data-hero-subtext
            className="text-body text-text-secondary max-w-xl mb-10 leading-relaxed"
          >
            3,000+ stocks filtered to the ones worth your capital. Every score auditable to the formula.
          </p>

          <div data-hero-ctas className="max-w-md">
            <HeroSearch />
            <p className="mt-4 text-sm text-text-secondary">
              or{" "}
              <Link
                href="/explore"
                className="text-text-secondary hover:text-accent transition-colors underline underline-offset-2"
              >
                browse this week&apos;s top picks &rarr;
              </Link>
            </p>
          </div>
        </div>

        {/* Right column — InstrumentPanel */}
        <div className="flex items-center justify-center lg:justify-end">
          <InstrumentPanel candidate={topCandidate} />
        </div>
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
