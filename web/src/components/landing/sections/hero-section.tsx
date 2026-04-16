"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import type { HomepageData } from "../shared/types"
import { HeroSearch } from "../hero-search"
import { InstrumentPanel } from "./instrument-panel"
import { CountUp } from "../shared/count-up"

interface HeroSectionProps {
  data: HomepageData | null
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (isNaN(then)) return "\u2014"
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const noiseRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const section = sectionRef.current
        if (!section) return
        section.querySelectorAll("[data-hero-headline] [data-word]").forEach((el) => {
          const htmlEl = el as HTMLElement
          htmlEl.style.opacity = "1"
          htmlEl.style.transform = "none"
          htmlEl.style.filter = "none"
        })
        const subtext = section.querySelector("[data-hero-subtext]") as HTMLElement | null
        const ctas = section.querySelector("[data-hero-ctas]") as HTMLElement | null
        const card = section.querySelector("[data-hero-card]") as HTMLElement | null
        const stats = section.querySelector("[data-hero-stats]") as HTMLElement | null
        if (subtext) subtext.style.opacity = "1"
        if (ctas) ctas.style.opacity = "1"
        if (card) card.style.opacity = "1"
        if (stats) stats.style.opacity = "1"
        return
      }

      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const section = sectionRef.current
      if (!section) return

      // Word-by-word headline reveal
      const words = section.querySelectorAll("[data-hero-headline] [data-word]")
      if (words.length > 0) {
        gsap.set(words, { opacity: 0, y: 20, filter: "blur(8px)" })
        gsap.to(words, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.55, stagger: 0.09, delay: 0.1, ease: "power2.out" })
      }

      // Subtext blur-up
      const subtext = section.querySelector("[data-hero-subtext]")
      if (subtext) {
        gsap.set(subtext, { opacity: 0, y: 16, filter: "blur(6px)" })
        gsap.to(subtext, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.45, ease: "power2.out" })
      }

      // Stats row blur-up
      const stats = section.querySelector("[data-hero-stats]")
      if (stats) {
        gsap.set(stats, { opacity: 0, y: 16, filter: "blur(4px)" })
        gsap.to(stats, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.55, ease: "power2.out" })
      }

      // CTAs blur-up
      const ctas = section.querySelector("[data-hero-ctas]")
      if (ctas) {
        gsap.set(ctas, { opacity: 0, y: 16, filter: "blur(4px)" })
        gsap.to(ctas, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.65, ease: "power2.out" })
      }

      // Card: scale + blur, no rotation, expo.out
      const card = section.querySelector("[data-hero-card]")
      if (card) {
        gsap.set(card, { opacity: 0, scale: 0.95, filter: "blur(10px)" })
        gsap.to(card, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.9, delay: 0.35, ease: "expo.out" })
      }

      // Parallax
      const grid = gridRef.current
      const noise = noiseRef.current
      if (grid) {
        gsap.to(grid, { y: 120, ease: "none", scrollTrigger: { trigger: section, start: "top top", end: "bottom top", scrub: true } })
        cleanups.push(() => ScrollTrigger.getAll().forEach((t) => t.kill()))
      }
      if (noise) {
        gsap.to(noise, { y: 60, ease: "none", scrollTrigger: { trigger: section, start: "top top", end: "bottom top", scrub: true } })
      }
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  const topCandidate = data?.candidates?.[0] ?? null

  return (
    <section id="hero" ref={sectionRef} className="relative flex items-center justify-center overflow-x-clip"
      style={{ minHeight: "80svh", background: "radial-gradient(ellipse 70% 55% at 50% 30%, rgba(128,216,178,0.08) 0%, transparent 60%), var(--color-surface)" }}>
      {/* Noise */}
      <div ref={noiseRef} className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: "url('/noise.svg')", backgroundRepeat: "repeat", opacity: 0.4, willChange: "transform" }} />
      {/* Grid */}
      <div ref={gridRef} className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: "linear-gradient(rgba(63,73,67,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(63,73,67,0.05) 1px, transparent 1px)", backgroundSize: "64px 64px", willChange: "transform" }} />

      <div className="grid grid-cols-1 lg:grid-cols-[60%_40%] gap-10 lg:gap-6 max-w-7xl w-full items-center pt-32 pb-24 px-6 relative z-10">
        <div className="flex flex-col justify-center">
          <h1 data-hero-headline className="text-display-lg uppercase mb-6">
            <span className="block" style={{ color: "var(--color-on-surface)" }}>
              <span data-word style={{ display: "inline-block" }}>DISCIPLINE</span>
            </span>
            <span className="block" style={{ color: "var(--color-primary)" }}>
              <span data-word style={{ display: "inline-block" }}>ENGINEERED</span>
            </span>
          </h1>

          <p data-hero-subtext className="text-body-md max-w-xl mb-8 leading-relaxed" style={{ color: "var(--color-on-surface-variant)" }}>
            A forensic scoring engine that replaces narrative with structure. {(data?.total_universe ?? 3056).toLocaleString()} US equities filtered to the ones worth your capital.
          </p>

          {/* Stats row — absorbed from Authority Strip */}
          <div data-hero-stats className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-10">
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.total_universe ?? 3056} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>UNIVERSE</div>
            </div>
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.total_scored ?? 0} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>SCORED</div>
            </div>
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.surviving_count ?? 0} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>SURVIVING</div>
            </div>
            <div>
              <div className="text-label-md" style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-data)" }}>
                {data?.last_updated ? formatRelativeTime(data.last_updated) : "\u2014"}
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>LAST CYCLE</div>
            </div>
          </div>

          <div data-hero-ctas className="max-w-md">
            <HeroSearch />
            <p className="mt-4 text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
              or{" "}
              <Link href="/explore" className="underline underline-offset-2 transition-colors duration-150 hover:text-[var(--color-primary)]"
                style={{ color: "var(--color-on-surface-variant)" }}>
                browse this week&apos;s top picks &rarr;
              </Link>
            </p>
          </div>
        </div>

        <div className="flex items-center justify-center lg:justify-end" data-hero-card>
          <InstrumentPanel candidate={topCandidate} />
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-32"
        style={{ background: "linear-gradient(to bottom, transparent, var(--color-surface))" }} />
    </section>
  )
}
