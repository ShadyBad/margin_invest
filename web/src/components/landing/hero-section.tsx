"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"
import { FALLBACK_CANDIDATES, DEFAULT_UNIVERSE_SIZE, DEFAULT_ELIGIBLE_COUNT, ENGINE_VERSION } from "./candidate-data"
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

      const targets = [headline, subtext, ctas, card].filter(Boolean)

      gsap.set(targets, { opacity: 0, y: 20 })

      targets.forEach((target, i) => {
        gsap.to(target, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          delay: i * 0.15,
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
        background: 'radial-gradient(ellipse 70% 60% at 75% 45%, rgba(26,122,90,0.10) 0%, transparent 65%), #0A0F0D',
      }}
    >
      {/* Grid overlay for depth */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            `linear-gradient(var(--color-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-grid-line) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          opacity: 0.5,
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 lg:gap-16 max-w-6xl w-full items-center pt-16 py-24 relative z-10">
        {/* Left column — headline + CTAs */}
        <div>
          {/* Eyebrow tag */}
          <div className="flex items-center gap-2 mb-5">
            <span
              className="inline-block w-1.5 h-1.5 rounded-full bg-accent animate-pulse"
            />
            <span className="font-mono text-[11px] uppercase tracking-widest text-accent">
              Engine {ENGINE_VERSION} &middot; Live
            </span>
          </div>

          <h1 data-hero-headline className="font-display leading-[1.05] tracking-tight mb-6" style={{ fontSize: "clamp(56px, 7.5vw, 96px)" }}>
            <span className="block text-text-primary">Discipline.</span>
            <span className="block" style={{ color: 'var(--color-accent)' }}>Engineered.</span>
          </h1>

          <p data-hero-subtext className="text-lg md:text-xl text-text-secondary max-w-lg mb-8 leading-relaxed">
            A deterministic capital allocation system that replaces narrative with structure.
            Search any ticker — the system shows you the quantitative evidence.
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

          {/* Trust micro-line */}
          <p className="font-mono text-[11px] text-text-tertiary mt-4 max-w-md">
            No credit card &middot; Free tier available &middot; 30-day guarantee on paid plans
          </p>
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
