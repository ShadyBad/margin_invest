"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

interface PickData {
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
}

interface ProofSectionProps {
  pick: PickData | null
}

const MOCK_FACTORS = { quality_percentile: 85, value_percentile: 62, momentum_percentile: 71 }

function PercentileBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20">{label}</span>
      <div className="flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-full"
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease }}
        />
      </div>
      <span className="font-mono text-xs text-text-primary w-8 text-right">{value}</span>
    </div>
  )
}

function ProofCard({ title, children }: { title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <motion.div
      ref={ref}
      className="terminal-card p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, ease }}
    >
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">{title}</p>
      {children}
    </motion.div>
  )
}

export function ProofSection({ pick }: ProofSectionProps) {
  const factors = pick ?? MOCK_FACTORS

  return (
    <section id="proof" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Structure creates measurable advantage.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Factor Transparency */}
          <ProofCard title="Factor Transparency">
            <div className="space-y-3">
              <PercentileBar label="Valuation" value={factors.value_percentile} />
              <PercentileBar label="Quality" value={factors.quality_percentile} />
              <PercentileBar label="Momentum" value={factors.momentum_percentile} />
              <PercentileBar label="Sentiment" value={68} />
              <PercentileBar label="Growth" value={74} />
            </div>
            <p className="text-xs text-text-tertiary mt-4">
              Every percentile visible. Every factor verifiable.
            </p>
          </ProofCard>

          {/* Card 2: Growth vs Value Tilt */}
          <ProofCard title="Growth vs Value Tilt">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs text-text-tertiary mb-1">
                  <span>Growth Weight</span>
                  <span className="font-mono">35%</span>
                </div>
                <div className="h-2 bg-bg-subtle rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-accent/70 rounded-full"
                    initial={{ width: 0 }}
                    whileInView={{ width: "35%" }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, ease }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs text-text-tertiary mb-1">
                  <span>Value Weight</span>
                  <span className="font-mono">25%</span>
                </div>
                <div className="h-2 bg-bg-subtle rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-accent/40 rounded-full"
                    initial={{ width: 0 }}
                    whileInView={{ width: "25%" }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.1, ease }}
                  />
                </div>
              </div>
            </div>
            <p className="text-xs text-text-tertiary mt-4">
              The engine adapts factor weights by growth stage automatically.
            </p>
          </ProofCard>

          {/* Card 3: Portfolio View (mock) */}
          <ProofCard title="Portfolio View">
            <div className="grid grid-cols-5 gap-1">
              {Array.from({ length: 25 }, (_, i) => {
                const opacity = 0.15 + Math.random() * 0.85
                return (
                  <div
                    key={i}
                    className="aspect-square rounded-sm bg-accent"
                    style={{ opacity }}
                  />
                )
              })}
            </div>
            <p className="text-xs text-text-tertiary mt-4">
              Correlation heatmap identifies position overlap before it matters.
            </p>
          </ProofCard>

          {/* Card 4: Historical Application (mock) */}
          <ProofCard title="Historical Application">
            <div className="h-24 flex items-end gap-1">
              {[40, 55, 48, 62, 58, 70, 65, 75, 72, 80, 78, 85].map((v, i) => (
                <motion.div
                  key={i}
                  className="flex-1 bg-accent/60 rounded-t-sm"
                  initial={{ height: 0 }}
                  whileInView={{ height: `${v}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.05, ease }}
                />
              ))}
            </div>
            <p className="text-xs text-text-tertiary mt-4">
              Backtested conviction vs actual returns. No curve-fitting.
            </p>
            <p className="text-[10px] text-text-tertiary mt-1 italic">
              Past performance is not indicative of future results.
            </p>
          </ProofCard>
        </div>
      </div>
    </section>
  )
}
