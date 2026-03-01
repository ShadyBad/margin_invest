"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"

interface FunnelData {
  universe_size: number
  survived_filters: number
  exceptional_count: number
  high_count: number
  medium_count: number
  last_scored_at: string | null
}

function formatCount(n: number): string {
  return n.toLocaleString()
}

function pct(part: number, whole: number): string {
  if (whole === 0) return "0%"
  return `${((part / whole) * 100).toFixed(1)}%`
}

const BARS: {
  key: keyof FunnelData
  label: (d: FunnelData) => string
  right: (d: FunnelData) => string
  color: string
}[] = [
  {
    key: "universe_size",
    label: (d) => `${formatCount(d.universe_size)} equities screened`,
    right: () => "100%",
    color: "bg-text-tertiary/30",
  },
  {
    key: "survived_filters",
    label: (d) => `${formatCount(d.survived_filters)} survived elimination`,
    right: (d) => pct(d.survived_filters, d.universe_size),
    color: "bg-accent/30",
  },
  {
    key: "high_count",
    label: (d) =>
      `${formatCount(d.high_count + d.exceptional_count)} High or Exceptional`,
    right: (d) => pct(d.high_count + d.exceptional_count, d.universe_size),
    color: "bg-accent/60",
  },
  {
    key: "exceptional_count",
    label: (d) => `${formatCount(d.exceptional_count)} Exceptional candidates`,
    right: (d) => pct(d.exceptional_count, d.universe_size),
    color: "bg-accent",
  },
]

const LABEL_THRESHOLD = 25

function getTooltipData(
  data: FunnelData,
  barIndex: number
): { stage: string; count: number; pctUniverse: string; pctPrevious: string | null } {
  const stages = [
    {
      stage: "Equities screened",
      count: data.universe_size,
      raw: data.universe_size,
      prevRaw: null as number | null,
    },
    {
      stage: "Survived elimination",
      count: data.survived_filters,
      raw: data.survived_filters,
      prevRaw: data.universe_size,
    },
    {
      stage: "High or Exceptional",
      count: data.high_count + data.exceptional_count,
      raw: data.high_count + data.exceptional_count,
      prevRaw: data.survived_filters,
    },
    {
      stage: "Exceptional candidates",
      count: data.exceptional_count,
      raw: data.exceptional_count,
      prevRaw: data.high_count + data.exceptional_count,
    },
  ]
  const s = stages[barIndex]
  return {
    stage: s.stage,
    count: s.count,
    pctUniverse: pct(s.raw, data.universe_size),
    pctPrevious: s.prevRaw !== null ? `${pct(s.raw, s.prevRaw)} of previous` : null,
  }
}

export function ProofSelectivityFunnel() {
  const [data, setData] = useState<FunnelData | null>(null)
  const [error, setError] = useState(false)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch("/api/v1/universe/funnel")
        if (resp.ok) {
          setData(await resp.json())
        } else {
          setError(true)
        }
      } catch {
        setError(true)
      }
    }
    load()
  }, [])

  if (error) {
    return (
      <div data-testid="funnel-error" className="text-center py-6">
        <p className="text-xs text-text-tertiary font-mono">
          Selectivity data unavailable
        </p>
      </div>
    )
  }

  if (!data) {
    return (
      <div data-testid="funnel-skeleton" className="space-y-3">
        {[100, 60, 20, 8].map((w, i) => (
          <div
            key={i}
            className="h-8 rounded bg-bg-subtle animate-pulse"
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    )
  }

  const maxVal = data.universe_size || 1

  return (
    <div aria-label="Selectivity funnel showing how many equities survive each scoring stage">
      <div className="space-y-2">
        {BARS.map((bar, i) => {
          const raw =
            bar.key === "high_count"
              ? data.high_count + data.exceptional_count
              : (data[bar.key] as number)
          const widthPct = Math.max(4, (raw / maxVal) * 100)
          const isExternal = widthPct < LABEL_THRESHOLD

          return (
            <motion.div
              key={bar.key}
              data-testid={`funnel-row-${bar.key}`}
              className="relative flex items-center gap-3"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <div
                data-testid="funnel-bar"
                className={`${bar.color} rounded h-8 shrink-0 ${
                  !isExternal ? "flex items-center justify-between px-3" : ""
                }`}
                style={{ width: `${widthPct}%` }}
              >
                {!isExternal && (
                  <>
                    <span className="text-xs text-text-primary font-mono truncate">
                      {bar.label(data)}
                    </span>
                    <span className="text-[10px] text-text-secondary font-mono ml-2 shrink-0">
                      {bar.right(data)}
                    </span>
                  </>
                )}
              </div>
              {isExternal && (
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-text-primary font-mono whitespace-nowrap">
                    {bar.label(data)}
                  </span>
                  <span className="text-[10px] text-text-secondary font-mono shrink-0">
                    {bar.right(data)}
                  </span>
                </div>
              )}
              {hoveredIndex === i && (
                <div
                  data-testid="funnel-tooltip"
                  className="absolute left-0 bottom-full mb-2 z-10 terminal-card px-3 py-2 text-xs font-mono shadow-lg min-w-[200px]"
                >
                  {(() => {
                    const tip = getTooltipData(data, i)
                    return (
                      <>
                        <p className="text-text-primary font-medium">{tip.stage}</p>
                        <p className="text-text-secondary">
                          {formatCount(tip.count)} &middot; {tip.pctUniverse} of universe
                        </p>
                        {tip.pctPrevious && (
                          <p className="text-text-tertiary">{tip.pctPrevious}</p>
                        )}
                      </>
                    )
                  })()}
                </div>
              )}
            </motion.div>
          )
        })}
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Most equities are eliminated before scoring begins.
      </p>
      <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
        Elimination removes stocks with insufficient data or failing fundamentals — not a
        quality judgment on the business.
      </p>
    </div>
  )
}
