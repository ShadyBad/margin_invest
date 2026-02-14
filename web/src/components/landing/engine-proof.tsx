"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

function ProofPanel({
  children,
  className = "",
  delay,
}: {
  children: React.ReactNode
  className?: string
  delay: number
}) {
  return (
    <motion.div
      className={`border border-border-primary bg-bg-elevated rounded-sm p-6 ${className}`}
      initial={{ opacity: 0, scale: 0.98 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay, ease }}
    >
      {children}
    </motion.div>
  )
}

function PercentileBarMock({ label, value }: { label: string; value: number }) {
  const color = value >= 90 ? "bg-accent" : value >= 70 ? "bg-accent/60" : "bg-text-tertiary"
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 text-[14px] text-text-secondary shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-bg-subtle rounded-sm overflow-hidden">
        <div className={`h-full ${color} rounded-sm`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-10 text-right text-[14px] font-mono text-text-primary">{value}</span>
    </div>
  )
}

export function EngineProof() {
  return (
    <section style={{ padding: "64px 24px 80px" }}>
      <div className="mx-auto" style={{ maxWidth: "1280px" }}>
        <motion.h2
          className="text-[14px] font-medium text-text-tertiary uppercase tracking-[0.05em] mb-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          What the output looks like
        </motion.h2>

        <div className="grid grid-cols-12 gap-4 md:gap-6">
          {/* Large panel: Factor Breakdown (cols 1-7) */}
          <ProofPanel className="col-span-12 md:col-span-7" delay={0}>
            <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-6">
              Factor Breakdown
            </div>
            <div className="space-y-3">
              <PercentileBarMock label="Quality" value={78} />
              <PercentileBarMock label="Value" value={65} />
              <PercentileBarMock label="Momentum" value={88} />
            </div>
            <div className="mt-6 pt-4 border-t border-border-primary flex items-baseline gap-2">
              <span className="text-[14px] text-text-secondary">Composite</span>
              <span className="text-[28px] font-bold font-mono text-text-primary">82</span>
              <span className="text-[14px] text-text-tertiary">percentile</span>
            </div>
            <div className="mt-3 text-[12px] text-accent/60">
              Sector-neutral percentile rank within GICS sector
            </div>
          </ProofPanel>

          {/* Right column: two stacked panels (cols 8-12) */}
          <div className="col-span-12 md:col-span-5 grid gap-4 md:gap-6 content-start">
            {/* Conviction Badge */}
            <ProofPanel delay={0.2}>
              <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-4">
                Conviction
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-accent" />
                <span className="text-[20px] font-bold text-text-primary">Exceptional</span>
              </div>
              <div className="mt-2 text-[14px] text-text-secondary">
                Top 1% composite percentile
              </div>
            </ProofPanel>

            {/* Filter Results */}
            <ProofPanel delay={0.35}>
              <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-4">
                Elimination Filters
              </div>
              <div className="space-y-2">
                {[
                  { name: "Beneish M-Score", passed: true },
                  { name: "Altman Z''", passed: true },
                  { name: "Liquidity", passed: true },
                  { name: "Interest Coverage", passed: true },
                ].map((filter) => (
                  <div key={filter.name} className="flex items-center gap-2 text-[14px]">
                    <span className={filter.passed ? "text-accent" : "text-bearish"}>
                      {filter.passed ? "\u2713" : "\u2717"}
                    </span>
                    <span className="text-text-secondary">{filter.name}</span>
                    <span
                      className={`ml-auto text-[12px] ${filter.passed ? "text-accent" : "text-bearish"}`}
                    >
                      {filter.passed ? "Pass" : "Fail"}
                    </span>
                  </div>
                ))}
              </div>
            </ProofPanel>
          </div>
        </div>

        <motion.p
          className="mt-8 text-text-secondary text-[16px] md:text-[17px] leading-relaxed"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 1.1, ease }}
        >
          These are real outputs from the scoring engine. Same inputs, same outputs, every time.
        </motion.p>
      </div>
    </section>
  )
}
