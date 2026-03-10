"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "../shared/types"
import { RadarChart } from "../visualizations/radar-chart"
import { FunnelDiagram } from "../visualizations/funnel-diagram"
import { MiniCandidateStack } from "../visualizations/mini-candidate-stack"

interface PipelineSectionProps {
  data: HomepageData | null
}

export function PipelineSection({ data }: PipelineSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const spreads = el.querySelectorAll<HTMLElement>("[data-editorial-spread]")
      spreads.forEach((spread, i) => {
        const fromX = i % 2 === 0 ? -40 : 40
        gsap.set(spread, { opacity: 0, x: fromX })
      })

      spreads.forEach((spread, i) => {
        const trigger = ScrollTrigger.create({
          trigger: spread,
          start: "top 85%",
          once: true,
          onEnter: () => {
            gsap.to(spread, {
              opacity: 1,
              x: 0,
              duration: 0.6,
              delay: i * 0.2,
              ease: "power2.out",
            })
          },
        })
        triggers.push(trigger)
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  const topCandidate = data?.candidates?.[0] ?? null

  const radarFactors = topCandidate
    ? {
        quality: topCandidate.quality_percentile,
        value: topCandidate.value_percentile,
        momentum: topCandidate.momentum_percentile,
        sentiment: topCandidate.sentiment_percentile,
        growth: topCandidate.growth_percentile,
      }
    : null

  return (
    <section id="pipeline" className="py-20 px-6">
      <div ref={sectionRef} className="max-w-5xl mx-auto">
        {/* Section headline */}
        <h2 className="text-display-2 text-center text-text-primary mb-16">
          From{" "}
          <span className="text-accent font-mono">
            {data ? data.total_universe.toLocaleString("en-US") : "---"}
          </span>{" "}
          stocks to the ones worth your screen.
        </h2>

        {/* ── Subsection 1: Eliminate (text left, visual right) ── */}
        <div data-editorial-spread className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Text */}
          <div>
            <h3 className="text-title-1 text-text-primary mb-4">
              Eliminate the Noise
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed mb-4">
              Six forensic filters run before a single score is calculated.
              Penny stocks, delistings, accounting manipulation (Beneish M-Score),
              bankruptcy risk (Altman Z-Score), illiquid names, and data-insufficient
              tickers are removed on sight.
            </p>
            {data && (
              <p className="font-mono text-xs text-text-tertiary">
                {(data.total_universe - data.eligible_count).toLocaleString("en-US")} eliminated
                {" / "}
                {data.eligible_count.toLocaleString("en-US")} remain
              </p>
            )}
          </div>

          {/* Visual: Funnel */}
          <div className="flex justify-center">
            {data ? (
              <FunnelDiagram
                universeCount={data.total_universe}
                eligibleCount={data.eligible_count}
                scoredCount={data.total_scored}
                survivingCount={data.surviving_count}
              />
            ) : (
              <div className="flex items-center justify-center min-h-[200px]">
                <span className="font-mono text-xs text-text-tertiary">
                  loads after scoring cycle
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Spacer */}
        <div className="py-16" />

        {/* ── Subsection 2: Score (visual left, text right) — REVERSED ── */}
        <div data-editorial-spread className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Visual: RadarChart */}
          <div className="flex justify-center md:order-1 order-2">
            {radarFactors ? (
              <div className="text-center">
                <RadarChart factors={radarFactors} size={220} />
                <div className="font-mono text-xs text-text-tertiary mt-2">
                  {topCandidate?.ticker} factor profile
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center min-h-[200px]">
                <span className="font-mono text-xs text-text-tertiary">
                  loads after scoring cycle
                </span>
              </div>
            )}
          </div>

          {/* Text */}
          <div className="md:order-2 order-1">
            <h3 className="text-title-1 text-text-primary mb-4">
              Score What Remains
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              Every survivor is ranked on five orthogonal factors: Quality, Value,
              Momentum, Sentiment, and Growth. Each factor is a percentile rank
              within the stock&apos;s GICS sector — not an arbitrary weighting.
              The composite score combines all five into a single number you can
              audit down to the formula.
            </p>
          </div>
        </div>

        {/* Spacer */}
        <div className="py-16" />

        {/* ── Subsection 3: Surface (text left, visual right) ── */}
        <div data-editorial-spread className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Text */}
          <div>
            <h3 className="text-title-1 text-text-primary mb-4">
              Surface the Survivors
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed mb-4">
              Only the highest-scoring positions survive to your screen. No
              opinions, no narratives — just the stocks that passed every filter
              and ranked highest across all five factors within their sector.
            </p>
            {data && (
              <p className="font-mono text-xs text-text-tertiary">
                {data.surviving_count} candidates surfaced from{" "}
                {data.total_universe.toLocaleString("en-US")}
              </p>
            )}
          </div>

          {/* Visual: MiniCandidateStack */}
          <div className="flex justify-center">
            <MiniCandidateStack candidates={data?.candidates ?? []} />
          </div>
        </div>
      </div>
    </section>
  )
}
