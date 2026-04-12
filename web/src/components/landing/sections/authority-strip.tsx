"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "../shared/types"
import { StalenessIndicator } from "../shared/staleness-indicator"

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

function formatNumber(n: number | undefined): string {
  if (n == null) return "\u2014"
  return n.toLocaleString("en-US")
}

export function AuthorityStrip({ data }: { data: HomepageData | null }) {
  const stripRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!stripRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = stripRef.current
      if (!el) return

      gsap.set(el, { opacity: 0, y: 30 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, y: 0, duration: 0.8, ease: "power2.out" })
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
    <section className="px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <div ref={stripRef} className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8">
          <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-4 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50 animate-pulse" />
            SYSTEM PROFILE
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
            {/* Universe */}
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-1">
                UNIVERSE
              </div>
              <div className="font-mono text-sm text-text-primary" data-testid="universe-value">
                {formatNumber(data?.total_universe)}
              </div>
              <div className="font-mono text-[10px] text-text-tertiary mt-0.5">
                equities tracked
              </div>
            </div>

            {/* Scored */}
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-1">
                SCORED
              </div>
              <div className="font-mono text-sm text-text-primary" data-testid="scored-value">
                {formatNumber(data?.total_scored)}
              </div>
              <div className="font-mono text-[10px] text-text-tertiary mt-0.5">
                five-factor analysis
              </div>
            </div>

            {/* Surviving */}
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-1">
                SURVIVING
              </div>
              <div className="font-mono text-sm text-text-primary" data-testid="surviving-value">
                {formatNumber(data?.surviving_count)}
              </div>
              <div className="font-mono text-[10px] text-text-tertiary mt-0.5">
                passed all filters
              </div>
            </div>

            {/* Last Cycle */}
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-1">
                LAST CYCLE
              </div>
              <div className="font-mono text-sm text-text-primary" data-testid="last-cycle-value">
                {data?.last_updated ? formatRelativeTime(data.last_updated) : "\u2014"}
              </div>
              <div className="font-mono text-[10px] text-text-tertiary mt-0.5">
                scoring engine
              </div>
            </div>
          </div>
        </div>

        {data?.isFallback && (
          <div className="mt-3 text-center">
            <StalenessIndicator isFallback />
          </div>
        )}
      </div>
    </section>
  )
}
