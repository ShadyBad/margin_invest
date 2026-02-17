"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"
import { HorizontalScroll } from "./horizontal-scroll"
import { GlassSurface } from "../ui/glass-surface"

const ease = [0.22, 1, 0.36, 1] as const

function Panel({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode
  title: string
  subtitle: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-10%" })

  return (
    <div
      ref={ref}
      data-engine-panel
      className="h-full flex items-center justify-center px-8 md:px-16"
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, ease }}
      >
        <GlassSurface className="max-w-xl p-8 md:p-12">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-text-tertiary)] mb-4">
            {subtitle}
          </p>
          <h2 className="font-display text-3xl md:text-4xl leading-tight text-[var(--color-text-primary)] mb-6">
            {title}
          </h2>
          {children}
        </GlassSurface>
      </motion.div>
    </div>
  )
}

export function ChapterEngine() {
  return (
    <HorizontalScroll>
      <Panel title="Raw Signal" subtitle="Step 1 of 3">
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          Earnings transcripts, SEC filings, price targets, institutional flows,
          insider transactions — hundreds of data points per ticker, gathered and
          normalized in real time.
        </p>
      </Panel>

      <Panel title="Structured Analysis" subtitle="Step 2 of 3">
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          Five scoring factors — valuation, quality, momentum, growth, and
          sentiment — each ranked against sector peers using percentile
          normalization. No opinions. No bias. Pure signal.
        </p>
      </Panel>

      <Panel title="Conviction Output" subtitle="Step 3 of 3">
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          A composite conviction score from 0 to 100 with a clear signal:
          strong buy, buy, hold, or avoid. Factor breakdowns show exactly
          what&apos;s driving the score.
        </p>
      </Panel>
    </HorizontalScroll>
  )
}
