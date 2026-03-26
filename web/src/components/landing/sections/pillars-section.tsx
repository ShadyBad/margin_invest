"use client"

import { useEffect, useRef } from "react"
import type { HomepageData, CandidateCard } from "../shared/types"

interface PillarsSectionProps {
  data: HomepageData | null
}

/* ── Filter list ── */

const FILTER_NAMES = [
  "Beneish M-Score",
  "Altman Z-Score",
  "Penny stock exclusion",
  "Delisting detection",
  "Liquidity threshold",
  "Data sufficiency",
]

/* ── Factor bar ── */

interface FactorBarProps {
  label: string
  value: number
}

function FactorBar({ label, value }: FactorBarProps) {
  return (
    <div className="group/bar flex items-center gap-3 cursor-default">
      <span className="text-xs text-text-tertiary w-24 shrink-0 transition-colors duration-200 group-hover/bar:text-text-secondary">{label}</span>
      <div className="relative flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden transition-all duration-200 group-hover/bar:bg-white/10">
        <div
          className="h-full bg-accent rounded-full transition-all duration-200 group-hover/bar:brightness-125"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="font-mono text-xs w-8 text-right text-text-secondary transition-colors duration-200 group-hover/bar:text-text-primary">
        {value}
      </span>
    </div>
  )
}

/* ── Sector distribution ── */

interface SectorCount {
  sector: string
  count: number
}

function buildSectorCounts(picks: CandidateCard[]): SectorCount[] {
  const map = new Map<string, number>()
  for (const p of picks) {
    map.set(p.sector, (map.get(p.sector) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .map(([sector, count]) => ({ sector, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
}

function SectorBar({ sector, count, maxCount }: SectorCount & { maxCount: number }) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0
  return (
    <div className="group/sector flex items-center gap-3 cursor-default">
      <span className="text-xs text-text-tertiary w-28 shrink-0 truncate transition-colors duration-200 group-hover/sector:text-text-secondary">
        {sector}
      </span>
      <div className="relative flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden transition-all duration-200 group-hover/sector:bg-white/10">
        <div
          className="h-full rounded-full transition-all duration-200 group-hover/sector:brightness-125"
          style={{
            width: `${pct}%`,
            background: "var(--color-accent)",
            opacity: 0.7,
          }}
        />
      </div>
      <span className="font-mono text-xs w-6 text-right text-text-secondary transition-colors duration-200 group-hover/sector:text-text-primary">
        {count}
      </span>
    </div>
  )
}

/* ── Null-data placeholder ── */

function DataPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full min-h-[120px]">
      <span className="font-mono text-xs text-text-tertiary">
        loads after scoring cycle
      </span>
    </div>
  )
}

/* ── Main component ── */

export function PillarsSection({ data }: PillarsSectionProps) {
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

      const cards = el.querySelectorAll<HTMLElement>("[data-pillar-card]")
      cards.forEach((card) => gsap.set(card, { opacity: 0, y: 24 }))

      cards.forEach((card, i) => {
        const trigger = ScrollTrigger.create({
          trigger: card,
          start: "top 85%",
          once: true,
          onEnter: () => {
            gsap.to(card, {
              opacity: 1,
              y: 0,
              duration: 0.6,
              delay: i * 0.1,
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

  const eliminationRate =
    data && data.total_universe > 0
      ? Math.round(
          ((data.total_universe - data.eligible_count) / data.total_universe) * 100
        )
      : null

  const topCandidate = data?.candidates?.[0] ?? null
  const sectorCounts = data?.allPicks ? buildSectorCounts(data.allPicks) : []
  const maxSectorCount = sectorCounts[0]?.count ?? 0

  return (
    <section id="pillars" className="py-20 px-6">
      <div ref={sectionRef} className="max-w-5xl mx-auto">
        {/* Section header */}
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-14 flex items-center gap-2 justify-center">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50" />
          THREE PILLARS
        </div>

        <div className="space-y-8">
          {/* ── Pillar 1: Elimination Filters ── */}
          <div
            data-pillar-card
            className="bg-bg-elevated border border-border-subtle rounded-xl overflow-hidden transition-all duration-300 hover:border-accent/25 hover:shadow-[0_4px_20px_rgba(26,122,90,0.06)]"
          >
            <div className="grid grid-cols-1 md:grid-cols-2">
              {/* Text column */}
              <div className="p-6 md:p-8">
                <h3 className="font-display text-xl md:text-2xl text-text-primary mb-3">
                  Elimination Filters
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed mb-5">
                  Six binary pass/fail tests run before a single score is
                  calculated. If a stock fails any one, it never reaches the
                  scoring engine.
                </p>
                <ul className="space-y-2">
                  {FILTER_NAMES.map((name) => (
                    <li
                      key={name}
                      className="flex items-center gap-2 text-xs text-text-secondary"
                    >
                      <span className="text-accent text-sm">&#10003;</span>
                      {name}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Data column */}
              <div className="p-6 md:p-8 border-t md:border-t-0 md:border-l border-border-subtle flex flex-col justify-center">
                {data ? (
                  <div className="space-y-4">
                    <div className="font-mono text-sm text-text-secondary">
                      Elimination Rate
                    </div>
                    <div className="font-mono text-3xl text-text-primary transition-transform duration-200 hover:scale-[1.03] origin-left cursor-default">
                      {eliminationRate}% eliminated
                    </div>
                    <div className="text-xs text-text-tertiary">
                      {data.eligible_count.toLocaleString("en-US")} of{" "}
                      {data.total_universe.toLocaleString("en-US")} passed
                    </div>
                    {topCandidate && (
                      <div className="mt-4 pt-4 border-t border-border-subtle">
                        <div className="font-mono text-xs text-text-tertiary">
                          Example
                        </div>
                        <div className="font-mono text-sm text-text-primary mt-1">
                          {topCandidate.ticker}: {topCandidate.filters_passed}/
                          {topCandidate.filters_total} passed
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <DataPlaceholder />
                )}
              </div>
            </div>
          </div>

          {/* ── Pillar 2: Multi-Factor Scoring ── */}
          <div
            data-pillar-card
            className="bg-bg-elevated border border-border-subtle rounded-xl overflow-hidden transition-all duration-300 hover:border-accent/25 hover:shadow-[0_4px_20px_rgba(26,122,90,0.06)]"
          >
            <div className="grid grid-cols-1 md:grid-cols-2">
              {/* Data column (left on desktop) */}
              <div className="p-6 md:p-8 md:order-1 order-2 border-t md:border-t-0 md:border-r border-border-subtle flex flex-col justify-center">
                {topCandidate ? (
                  <div className="space-y-4">
                    <div>
                      <div className="font-mono text-lg font-bold text-text-primary">
                        {topCandidate.ticker}
                      </div>
                      <div className="text-xs text-text-secondary truncate">
                        {topCandidate.name}
                      </div>
                    </div>
                    <div className="font-mono text-3xl text-accent transition-transform duration-200 hover:scale-[1.03] origin-left cursor-default">
                      {topCandidate.score}
                    </div>
                    <div className="space-y-2.5">
                      <FactorBar
                        label="Quality"
                        value={topCandidate.quality_percentile}
                      />
                      <FactorBar
                        label="Value"
                        value={topCandidate.value_percentile}
                      />
                      <FactorBar
                        label="Momentum"
                        value={topCandidate.momentum_percentile}
                      />
                      <FactorBar
                        label="Sentiment"
                        value={topCandidate.sentiment_percentile ?? 0}
                      />
                      <FactorBar
                        label="Growth"
                        value={topCandidate.growth_percentile ?? 0}
                      />
                    </div>
                  </div>
                ) : (
                  <DataPlaceholder />
                )}
              </div>

              {/* Text column (right on desktop) */}
              <div className="p-6 md:p-8 md:order-2 order-1">
                <h3 className="font-display text-xl md:text-2xl text-text-primary mb-3">
                  Multi-Factor Scoring
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  Every surviving stock is ranked on five orthogonal factors:
                  Quality, Value, Momentum, Sentiment, and Growth. Each factor is
                  a percentile rank within the stock&apos;s GICS sector, not an
                  arbitrary weighting. The composite score combines all five into
                  a single number you can audit down to the formula.
                </p>
              </div>
            </div>
          </div>

          {/* ── Pillar 3: Sector-Neutral Ranking ── */}
          <div
            data-pillar-card
            className="bg-bg-elevated border border-border-subtle rounded-xl overflow-hidden transition-all duration-300 hover:border-accent/25 hover:shadow-[0_4px_20px_rgba(26,122,90,0.06)]"
          >
            <div className="grid grid-cols-1 md:grid-cols-2">
              {/* Text column */}
              <div className="p-6 md:p-8">
                <h3 className="font-display text-xl md:text-2xl text-text-primary mb-3">
                  Sector-Neutral Ranking
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  A bank and a tech company have different ROICs, margins, and
                  capital structures. Comparing them on the same scale produces
                  garbage. Margin Invest ranks every factor within GICS sector
                  peers first, then combines. The result: you get the best stock
                  in each sector, not just the sector with the highest raw
                  numbers.
                </p>
              </div>

              {/* Data column */}
              <div className="p-6 md:p-8 border-t md:border-t-0 md:border-l border-border-subtle flex flex-col justify-center">
                {sectorCounts.length > 0 ? (
                  <div className="space-y-4">
                    <div className="font-mono text-sm text-text-secondary">
                      Current Picks by Sector
                    </div>
                    <div className="space-y-2.5">
                      {sectorCounts.map((sc) => (
                        <SectorBar
                          key={sc.sector}
                          sector={sc.sector}
                          count={sc.count}
                          maxCount={maxSectorCount}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <DataPlaceholder />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
