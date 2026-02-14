"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const filterItems = ["Beneish M-Score", "Altman Z''", "Liquidity", "Coverage"]
const qualityItems = ["Gross Profitability", "ROIC-WACC", "Accrual Ratio", "F-Score"]
const valueItems = ["EV/FCF", "Shareholder Yield", "DCF Margin", "Acquirer's Multiple"]
const momentumItems = ["Price 12-1mo", "Earnings SUE", "Insider Clusters", "Institutional Flow"]
const classificationItems = ["Exceptional", "High Conviction", "Watchlist"]

function DiagramNode({
  x, y, width, height, label, sublabel, items, delay, isActive, inView,
}: {
  x: number; y: number; width: number; height: number
  label: string; sublabel?: string; items?: string[]
  delay: number; isActive?: boolean; inView: boolean
}) {
  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.96 }}
      animate={inView ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.5, delay, ease }}
    >
      <motion.rect
        x={x} y={y} width={width} height={height}
        fill="none"
        className={isActive ? "stroke-accent" : "stroke-border-primary"}
        strokeWidth={1}
        rx={2}
      />
      <motion.text
        x={x + 12} y={y + 22}
        className="fill-text-primary"
        fontFamily="var(--font-inter-tight)"
        fontSize={13} fontWeight={600}
      >
        {label}
      </motion.text>
      {sublabel && (
        <motion.text
          x={x + 12} y={y + 38}
          className="fill-text-tertiary"
          fontFamily="var(--font-inter-tight)"
          fontSize={11}
        >
          {sublabel}
        </motion.text>
      )}
      {items?.map((item, i) => (
        <motion.text
          key={item}
          x={x + 12} y={y + (sublabel ? 56 : 42) + i * 16}
          className="fill-text-secondary"
          fontFamily="var(--font-inter-tight)"
          fontSize={11}
        >
          {item}
        </motion.text>
      ))}
    </motion.g>
  )
}

function Connector({ x1, y1, x2, y2, delay, inView }: {
  x1: number; y1: number; x2: number; y2: number; delay: number; inView: boolean
}) {
  const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
  return (
    <motion.line
      x1={x1} y1={y1} x2={x2} y2={y2}
      className="stroke-border-primary"
      strokeWidth={1}
      strokeDasharray={length}
      strokeDashoffset={length}
      animate={inView ? { strokeDashoffset: 0 } : {}}
      transition={{ duration: 0.6, delay, ease }}
    />
  )
}

export function SystemDiagram() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-15% 0px" })

  return (
    <section ref={ref} style={{ padding: "96px 24px" }}>
      <div className="mx-auto" style={{ maxWidth: "1280px" }}>
        <motion.h2
          className="text-[14px] font-medium text-text-tertiary uppercase tracking-[0.05em] mb-12"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.4, ease }}
        >
          How the engine works
        </motion.h2>

        {/* Desktop diagram */}
        <div className="hidden lg:block">
          <svg viewBox="0 0 960 420" className="w-full" aria-label="Scoring pipeline diagram">
            {/* Elimination Filters */}
            <DiagramNode x={0} y={30} width={180} height={160} label="Elimination Filters" items={filterItems} delay={0.2} inView={inView} />

            {/* Connector: Filters → Scoring */}
            <Connector x1={180} y1={110} x2={240} y2={110} delay={0.5} inView={inView} />

            {/* Quality */}
            <DiagramNode x={240} y={0} width={200} height={130} label="Quality" sublabel="35%" items={qualityItems} delay={0.7} inView={inView} />

            {/* Value */}
            <DiagramNode x={240} y={145} width={200} height={130} label="Value" sublabel="30%" items={valueItems} delay={0.85} inView={inView} />

            {/* Momentum */}
            <DiagramNode x={240} y={290} width={200} height={130} label="Momentum" sublabel="35%" items={momentumItems} delay={1.0} inView={inView} />

            {/* Connectors: Scoring → Composite */}
            <Connector x1={440} y1={65} x2={500} y2={195} delay={1.2} inView={inView} />
            <Connector x1={440} y1={210} x2={500} y2={210} delay={1.2} inView={inView} />
            <Connector x1={440} y1={355} x2={500} y2={225} delay={1.2} inView={inView} />

            {/* Composite Score */}
            <DiagramNode x={500} y={170} width={190} height={80} label="Composite Score" sublabel="Sector-neutral percentile" delay={1.5} isActive inView={inView} />

            {/* Connector: Composite → Classification */}
            <Connector x1={690} y1={210} x2={750} y2={210} delay={1.8} inView={inView} />

            {/* Classification */}
            <DiagramNode x={750} y={150} width={180} height={120} label="Classification" items={classificationItems} delay={2.1} inView={inView} />
          </svg>
        </div>

        {/* Mobile: simplified vertical flow */}
        <div className="lg:hidden space-y-4">
          {[
            { label: "Elimination Filters", sub: filterItems.join(" · ") },
            { label: "Quality (35%)", sub: qualityItems.join(" · ") },
            { label: "Value (30%)", sub: valueItems.join(" · ") },
            { label: "Momentum (35%)", sub: momentumItems.join(" · ") },
            { label: "Composite Score", sub: "Sector-neutral percentile ranking" },
            { label: "Classification", sub: classificationItems.join(" · ") },
          ].map((stage, i) => (
            <motion.div
              key={stage.label}
              className="border border-border-primary rounded-sm p-4"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <div className="text-[14px] font-semibold text-text-primary">{stage.label}</div>
              <div className="text-[12px] text-text-secondary mt-1">{stage.sub}</div>
            </motion.div>
          ))}
        </div>

        <motion.p
          className="mt-10 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[800px]"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.45, delay: 2.4, ease }}
        >
          Every asset passes through the same pipeline. Elimination filters remove manipulated or distressed companies before scoring begins. Remaining assets are ranked within their sector, then classified by composite percentile.
        </motion.p>
      </div>
    </section>
  )
}
