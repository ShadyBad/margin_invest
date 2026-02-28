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
      className="min-h-screen flex items-center justify-center bg-bg-primary px-6"
    >
      <div className="grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 lg:gap-16 max-w-6xl w-full items-center py-24">
        {/* Left column — headline + CTAs */}
        <div>
          <h1 data-hero-headline className="font-display text-5xl md:text-7xl lg:text-[80px] leading-[1.05] tracking-tight mb-6">
            <span className="block text-text-primary">Discipline.</span>
            <span className="block text-accent">Engineered.</span>
          </h1>

          <p data-hero-subtext className="text-lg md:text-xl text-text-secondary max-w-lg mb-10 leading-relaxed">
            A deterministic capital allocation system that replaces narrative with structure.
            Search any ticker — the system shows you the quantitative evidence.
          </p>

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
    </section>
  )
}
