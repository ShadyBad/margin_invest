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

export function ProofSelectivityFunnel() {
  const [data, setData] = useState<FunnelData | null>(null)
  const [error, setError] = useState(false)

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
          return (
            <motion.div
              key={bar.key}
              className="relative"
              initial={{ width: 0 }}
              whileInView={{ width: "100%" }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <div
                className={`${bar.color} rounded h-8 flex items-center justify-between px-3`}
                style={{ width: `${widthPct}%` }}
              >
                <span className="text-xs text-text-primary font-mono truncate">
                  {bar.label(data)}
                </span>
                <span className="text-[10px] text-text-secondary font-mono ml-2 shrink-0">
                  {bar.right(data)}
                </span>
              </div>
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
