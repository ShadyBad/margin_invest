"use client"

import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion"
import { useRef, useEffect } from "react"

const ease = [0.22, 1, 0.36, 1] as const
const dataEase = [0.16, 1, 0.3, 1] as const

function AnimatedNumber({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const motionValue = useMotionValue(0)
  const display = useTransform(motionValue, (v) => v.toFixed(decimals))

  useEffect(() => {
    if (!isInView) return
    const controls = animate(motionValue, value, {
      duration: 1.2,
      ease: dataEase,
    })
    return controls.stop
  }, [isInView, motionValue, value])

  useEffect(() => {
    const unsubscribe = display.on("change", (v) => {
      if (ref.current) ref.current.textContent = v
    })
    return unsubscribe
  }, [display])

  return <span ref={ref}>0.0</span>
}

function AnimatedBar({ width, color, delay }: { width: number; color: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true })

  return (
    <div ref={ref} className="flex-1 h-[6px] bg-bg-subtle rounded-sm overflow-hidden">
      <motion.div
        className={`h-full ${color} rounded-sm`}
        initial={{ width: "0%" }}
        animate={isInView ? { width: `${width}%` } : { width: "0%" }}
        transition={{ duration: 0.8, delay, ease: dataEase }}
      />
    </div>
  )
}

function CompositeScorePanel() {
  const barRef = useRef<HTMLDivElement>(null)
  const isInView = useInView(barRef, { once: true })

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Composite Score
        </span>
        <span className="text-[11px] font-mono text-text-secondary">Sample Output</span>
      </div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-[36px] font-bold text-text-primary leading-none tracking-[-1px]">
          <AnimatedNumber value={78.4} />
        </span>
        <span className="text-[13px] text-accent font-medium">/100</span>
      </div>
      <div ref={barRef} className="w-full h-2 bg-bg-subtle rounded-sm overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-sm"
          initial={{ width: "0%" }}
          animate={isInView ? { width: "78.4%" } : { width: "0%" }}
          transition={{ duration: 0.8, delay: 0.2, ease: dataEase }}
        />
      </div>
      <div className="flex justify-between mt-2 text-[11px] text-text-secondary font-mono">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  )
}

function RiskBreakdownPanel() {
  const risks = [
    { label: "Drawdown", value: 34, color: "bg-accent" },
    { label: "Volatility", value: 52, color: "bg-text-secondary" },
    { label: "Sector Conc.", value: 18, color: "bg-accent" },
    { label: "Liquidity", value: 8, color: "bg-text-secondary" },
  ]

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Risk Breakdown
        </span>
        <span className="text-[11px] font-mono text-accent">Low–Med</span>
      </div>
      <div className="flex flex-col gap-3">
        {risks.map((risk, i) => (
          <div key={risk.label} className="flex items-center gap-3">
            <span className="text-[12px] text-text-secondary w-20 flex-shrink-0 font-mono">
              {risk.label}
            </span>
            <AnimatedBar width={risk.value} color={risk.color} delay={0.1 + i * 0.08} />
            <span className="text-[11px] text-text-secondary font-mono w-6 text-right">
              {risk.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function FactorWeightsPanel() {
  const factors = [
    { label: "Value", weight: 25, percentile: 82 },
    { label: "Momentum", weight: 20, percentile: 71 },
    { label: "Quality", weight: 30, percentile: 88 },
    { label: "Growth", weight: 15, percentile: 62 },
    { label: "Stability", weight: 10, percentile: 79 },
  ]

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Factor Weights
        </span>
        <span className="text-[11px] font-mono text-text-secondary">5 factors</span>
      </div>
      <div className="flex flex-col gap-2.5">
        {factors.map((f, i) => (
          <div key={f.label} className="flex items-center gap-3">
            <span className="text-[12px] text-text-secondary w-16 flex-shrink-0">
              {f.label}
            </span>
            <AnimatedBar width={f.percentile} color="bg-accent" delay={0.1 + i * 0.06} />
            <span className="text-[11px] text-text-secondary font-mono w-8 text-right">
              P{f.percentile}
            </span>
            <span className="text-[10px] text-text-secondary font-mono w-8 text-right opacity-50">
              {f.weight}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MethodologyLink() {
  return (
    <motion.p
      className="text-[12px] text-text-tertiary mt-4 text-right font-mono"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: 0.5 }}
    >
      Deterministic output from the Margin scoring engine.{" "}
      <a href="/methodology" className="text-accent hover:underline">
        Methodology documentation &rarr;
      </a>
    </motion.p>
  )
}

export function EngineProof() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "80px",
        }}
      >
        <motion.div
          className="col-span-4 md:col-span-4 lg:col-span-4 flex flex-col justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            What the engine produces.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
            Every equity receives a deterministic composite score, risk profile,
            and factor-weighted breakdown — no narrative, no discretion.
          </p>
        </motion.div>

        <div className="col-span-4 md:col-start-5 md:col-span-4 lg:col-start-6 lg:col-span-7 flex flex-col gap-4">
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0, ease }}
          >
            <CompositeScorePanel />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15, ease }}
          >
            <RiskBreakdownPanel />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3, ease }}
          >
            <FactorWeightsPanel />
          </motion.div>
          <MethodologyLink />
        </div>
      </div>
    </section>
  )
}
