"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"
import { HeroSearch } from "./hero-search"

interface HeroSectionProps {
  data: HomepageData | null
  totalUniverse: number
  survivingCount: number
}

export function HeroSection({ data, totalUniverse, survivingCount }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const indictmentRef = useRef<HTMLDivElement>(null)
  const subtextRef = useRef<HTMLParagraphElement>(null)
  const brandRef = useRef<HTMLDivElement>(null)
  const searchWrapperRef = useRef<HTMLDivElement>(null)
  const indicatorRef = useRef<HTMLDivElement>(null)

  // Use data-driven universe size if available, otherwise fall back to props
  const universeSize = data?.total_universe ?? totalUniverse
  const survivors = data?.surviving_count ?? survivingCount

  const eliminationPct =
    universeSize > 0 ? Math.round((1 - survivors / universeSize) * 100) : 94

  useEffect(() => {
    let cancelled = false
    const tweens: Array<{ kill: () => void }> = []
    const scrollTriggers: Array<{ kill: () => void }> = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const section = sectionRef.current
      const indictment = indictmentRef.current
      const subtext = subtextRef.current
      const brand = brandRef.current
      const searchWrapper = searchWrapperRef.current
      const indicator = indicatorRef.current

      if (!section) return

      // Phase 1: Fade in indictment on load
      if (indictment) {
        tweens.push(
          gsap.from(indictment, {
            opacity: 0,
            y: 20,
            duration: 0.6,
            delay: 0.4,
            ease: "power2.out",
          })
        )
      }
      if (subtext) {
        tweens.push(
          gsap.from(subtext, {
            opacity: 0,
            y: 12,
            duration: 0.6,
            delay: 0.6,
            ease: "power2.out",
          })
        )
      }

      // Phase 2: Scroll-driven — indictment fades out, brand fades in
      if (indictment && brand) {
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: "30% top",
            scrub: true,
          },
        })

        tl.to(indictment, { opacity: 0, scale: 0.97 })
        tl.fromTo(brand, { y: 40, opacity: 0 }, { y: 0, opacity: 1 }, 0)

        const st = tl.scrollTrigger
        if (st) scrollTriggers.push(st as unknown as { kill: () => void })
      }

      // Phase 3: Scroll-driven — subtext + search reveal
      if (searchWrapper) {
        const tl2 = gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: "60% top",
            end: "80% top",
            scrub: true,
          },
        })

        tl2.fromTo(searchWrapper, { opacity: 0, y: 20 }, { opacity: 1, y: 0 })

        const st2 = tl2.scrollTrigger
        if (st2) scrollTriggers.push(st2 as unknown as { kill: () => void })
      }

      // Scroll indicator pulse
      if (indicator) {
        tweens.push(
          gsap.to(indicator, {
            opacity: 0.3,
            duration: 1.5,
            repeat: -1,
            yoyo: true,
          })
        )
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      tweens.forEach((t) => t.kill())
      scrollTriggers.forEach((st) => st.kill())
    }
  }, [])

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative flex items-center justify-center"
      style={{ minHeight: "100svh" }}
    >
      <div className="max-w-4xl w-full text-center px-6 relative z-10">
        {/* Phase 1: Indictment */}
        <div ref={indictmentRef}>
          <p
            className="font-mono leading-none tracking-tight"
            style={{ fontSize: "clamp(48px, 8vw, 96px)" }}
          >
            {eliminationPct}% eliminated.
          </p>
          <p
            ref={subtextRef}
            className="text-base md:text-lg text-text-secondary mt-4 font-mono"
          >
            {universeSize.toLocaleString()} US equities scored.{" "}
            {survivors > 0 ? survivors.toLocaleString() : "\u2014"} survived.
          </p>
        </div>

        {/* Phase 2: Brand reveal (starts hidden, revealed by scroll) */}
        <div ref={brandRef} style={{ opacity: 0 }} className="mt-16">
          <h1
            className="font-display leading-[1.05] tracking-tight"
            style={{ fontSize: "clamp(48px, 7vw, 72px)" }}
          >
            <span className="block text-text-primary">Discipline.</span>
            <span className="block" style={{ color: "var(--color-accent)" }}>
              Engineered.
            </span>
          </h1>
        </div>

        {/* Phase 3: Subtext + Search (starts hidden, revealed by scroll) */}
        <div ref={searchWrapperRef} style={{ opacity: 0 }} className="mt-10">
          <p className="text-lg md:text-xl text-text-secondary max-w-xl mx-auto mb-10 leading-relaxed">
            A deterministic scoring engine for{" "}
            {universeSize.toLocaleString()} US equities. No opinions. No
            overrides. Search one.
          </p>
          <HeroSearch />
        </div>
      </div>

      {/* Scroll indicator */}
      <div
        ref={indicatorRef}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        style={{ opacity: 0.6 }}
      >
        <div className="w-px h-8 bg-text-tertiary" />
      </div>
    </section>
  )
}
