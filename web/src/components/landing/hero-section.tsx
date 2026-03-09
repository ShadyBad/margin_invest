"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"
import { FALLBACK_CANDIDATES, DEFAULT_UNIVERSE_SIZE, DEFAULT_ELIGIBLE_COUNT } from "./candidate-data"
import { HeroCandidateCard } from "./hero-candidate-card"
import { HeroSearch } from "./hero-search"

interface HeroSectionProps {
  data: HomepageData | null
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  const candidates = data?.candidates ?? FALLBACK_CANDIDATES
  const universeSize = data?.universe_size ?? DEFAULT_UNIVERSE_SIZE
  const eligibleCount = data?.eligible_count ?? DEFAULT_ELIGIBLE_COUNT

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
      const ctas = section.querySelector("[data-hero-ctas]")
      const card = section.querySelector("[data-hero-card]")

      const textTargets = [headline, subtext, ctas].filter(Boolean)
      gsap.set(textTargets, { opacity: 0, y: 20 })

      // Card loads instantly — no delay on the strongest trust signal
      if (card) {
        gsap.set(card, { opacity: 0, y: 12 })
        gsap.to(card, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" })
      }

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

    animate().catch(() => {
      // Silently handle module resolution failures during test teardown
    })

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
        minHeight: '100svh',
        background: 'radial-gradient(ellipse 50% 50% at 85% 25%, rgba(201,150,59,0.06) 0%, transparent 60%), radial-gradient(ellipse 70% 60% at 75% 45%, rgba(26,122,90,0.10) 0%, transparent 65%), var(--color-bg-primary)',
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
            `linear-gradient(var(--color-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-grid-line) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          opacity: 1,
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 lg:gap-16 max-w-6xl w-full items-center pt-16 py-24 relative z-10">
        {/* Left column — headline + CTAs */}
        <div>
          <h1 data-hero-headline className="font-display leading-[1.05] tracking-tight mb-6" style={{ fontSize: "clamp(56px, 7.5vw, 96px)" }}>
            <span className="block text-text-primary">Discipline.</span>
            <span className="block" style={{ color: 'var(--color-accent)' }}>Engineered.</span>
          </h1>

          <p data-hero-subtext className="text-lg md:text-xl text-text-secondary max-w-lg mb-8 leading-relaxed">
            A deterministic scoring engine for 3,056 US equities. No opinions. No overrides. Search one.
          </p>

          {/* Divider */}
          <div
            className="w-16 mb-8"
            style={{
              height: "1px",
              background: `linear-gradient(90deg, var(--color-accent), transparent)`,
            }}
          />

          <HeroSearch />
        </div>

        {/* Right column — rotating card */}
        <div data-hero-card>
          <HeroCandidateCard
            candidates={candidates}
            universeSize={universeSize}
            eligibleCount={eligibleCount}
          />
        </div>
      </div>

      {/* Bottom fade gradient that bleeds into next section */}
      <div
        className="pointer-events-none absolute bottom-0 left-0 right-0 h-32"
        style={{
          background: `linear-gradient(to bottom, transparent, var(--color-bg-primary))`,
        }}
      />
    </section>
  )
}
