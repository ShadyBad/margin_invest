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
      data-proof-panel
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

export function ChapterProof() {
  return (
    <HorizontalScroll>
      <Panel title="Sample Analysis" subtitle="Conviction in action">
        <div className="space-y-4">
          <div className="flex items-baseline justify-between">
            <span className="font-display text-2xl text-[var(--color-text-primary)]">AAPL</span>
            <span className="text-3xl font-display text-[var(--color-accent)]">78</span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Strong Buy — driven by quality fundamentals and institutional
            accumulation. Valuation factor slightly below median.
          </p>
        </div>
      </Panel>

      <Panel title="Factor Depth" subtitle="Under the hood">
        <div className="space-y-3">
          {[
            { name: "Valuation", score: 62 },
            { name: "Quality", score: 85 },
            { name: "Momentum", score: 71 },
            { name: "Growth", score: 68 },
            { name: "Sentiment", score: 89 },
          ].map((factor) => (
            <div key={factor.name} className="flex items-center gap-3">
              <span className="text-xs w-20 text-[var(--color-text-tertiary)]">{factor.name}</span>
              <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border-subtle)]">
                <div
                  className="h-full rounded-full bg-[var(--color-accent)]"
                  style={{ width: `${factor.score}%` }}
                />
              </div>
              <span className="text-xs w-8 text-right text-[var(--color-text-secondary)]">
                {factor.score}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Portfolio View" subtitle="Comparative conviction">
        <div className="space-y-2">
          {[
            { ticker: "AAPL", score: 78, signal: "Strong Buy" },
            { ticker: "MSFT", score: 72, signal: "Buy" },
            { ticker: "GOOGL", score: 65, signal: "Buy" },
            { ticker: "NVDA", score: 58, signal: "Hold" },
            { ticker: "AMZN", score: 45, signal: "Hold" },
          ].map((item) => (
            <div
              key={item.ticker}
              className="flex items-center justify-between py-2 border-b border-[var(--color-border-subtle)]"
            >
              <span className="font-medium text-[var(--color-text-primary)]">{item.ticker}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-[var(--color-text-tertiary)]">{item.signal}</span>
                <span className="font-display text-lg text-[var(--color-accent)]">
                  {item.score}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </HorizontalScroll>
  )
}
