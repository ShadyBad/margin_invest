"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

interface PickData {
  ticker: string
  name: string
  actual_price: number | null
  buy_price: number | null
  margin_of_safety: number | null
  composite_percentile: number
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  scored_at: string | null
  sector: string | null
}

const MOCK_PICK: PickData = {
  ticker: "AAPL",
  name: "Apple Inc.",
  actual_price: 173.22,
  buy_price: 214.9,
  margin_of_safety: 0.194,
  composite_percentile: 83,
  quality_percentile: 85,
  value_percentile: 62,
  momentum_percentile: 71,
  scored_at: new Date().toISOString(),
  sector: "Technology",
}

const ease = [0.22, 1, 0.36, 1] as const

function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-full"
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary w-8 text-right">{Math.round(value)}</span>
    </div>
  )
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "\u2014"
  const d = new Date(iso)
  const h = d.getHours().toString().padStart(2, "0")
  const m = d.getMinutes().toString().padStart(2, "0")
  return `Last recalculated ${h}:${m} EST`
}

interface HeroCandidatePanelProps {
  pick: PickData | null
}

export function HeroCandidatePanel({ pick }: HeroCandidatePanelProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })
  const data = pick ?? MOCK_PICK

  const mosPercent =
    data.margin_of_safety != null
      ? `${(data.margin_of_safety * 100).toFixed(1)}%`
      : "\u2014"

  return (
    <motion.div
      ref={ref}
      className="terminal-card p-6 md:p-8 w-full max-w-sm"
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: 0.3, ease }}
    >
      {/* Header */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <span className="font-mono text-lg font-semibold text-text-primary">{data.ticker}</span>
          <span className="ml-2 text-xs text-text-tertiary">{data.name}</span>
        </div>
        {data.sector && (
          <span className="text-[10px] uppercase tracking-widest text-text-tertiary">
            {data.sector}
          </span>
        )}
      </div>

      {/* Price row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Current</p>
          <p className="font-mono text-xl text-text-primary">
            ${data.actual_price?.toFixed(2) ?? "\u2014"}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Target</p>
          <p className="font-mono text-xl text-text-primary">
            ${data.buy_price?.toFixed(2) ?? "\u2014"}
          </p>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
            Margin of Safety
          </p>
          <p className="font-mono text-lg text-accent">{mosPercent}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
            Conviction Score
          </p>
          <p className="font-mono text-lg text-text-primary">{data.composite_percentile}</p>
        </div>
      </div>

      {/* Factor bars */}
      <div className="space-y-2.5 mb-6">
        <FactorBar label="Quality" value={data.quality_percentile} />
        <FactorBar label="Value" value={data.value_percentile} />
        <FactorBar label="Momentum" value={data.momentum_percentile} />
      </div>

      {/* Timestamp */}
      <p className="font-mono text-[10px] text-text-tertiary text-right">
        {formatTimestamp(data.scored_at)}
      </p>
    </motion.div>
  )
}
