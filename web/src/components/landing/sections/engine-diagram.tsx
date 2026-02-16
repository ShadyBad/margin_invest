"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { useRef, useEffect, useCallback } from "react"
import { useNodePositions } from "@/lib/stores/node-positions"

const ease = [0.22, 1, 0.36, 1] as const

function MarketDataIcon({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor">
      <line x1="6" y1="22" x2="30" y2="22" />
      <line x1="9" y1="22" x2="9" y2="8" />
      <line x1="18" y1="22" x2="18" y2="4" />
      <line x1="27" y1="22" x2="27" y2="12" />
    </svg>
  )
}

function RiskModelingIcon({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor">
      <polyline points="14,7 22,10 14,13" />
      <polyline points="12,15 22,18 12,21" />
      <polyline points="10,23 22,26 10,29" />
    </svg>
  )
}

function AllocationEngineIcon({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor">
      <circle cx="18" cy="18" r="12" />
      <line x1="18" y1="18" x2="18" y2="6" />
      <line x1="18" y1="18" x2="7.6" y2="24" />
      <line x1="18" y1="18" x2="27.2" y2="23.3" />
    </svg>
  )
}

function DecisionClarityIcon({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor">
      <line x1="6" y1="18" x2="30" y2="18" />
      <line x1="18" y1="6" x2="18" y2="30" />
      <circle cx="18" cy="18" r="3" />
    </svg>
  )
}

type IconComponent = ({ size }: { size?: number }) => React.JSX.Element

const nodes: { label: string; desc: string; Icon: IconComponent }[] = [
  { label: "Market Data", desc: "Real-time feeds", Icon: MarketDataIcon },
  { label: "Risk Modeling", desc: "Factor analysis", Icon: RiskModelingIcon },
  { label: "Allocation Engine", desc: "Score synthesis", Icon: AllocationEngineIcon },
  { label: "Decision Clarity", desc: "Actionable output", Icon: DecisionClarityIcon },
]

function Arrow() {
  return (
    <div className="hidden lg:flex items-center justify-center flex-shrink-0 w-12">
      <svg width="48" height="12" viewBox="0 0 48 12" fill="none" className="text-border-primary">
        <line x1="0" y1="6" x2="38" y2="6" stroke="currentColor" strokeWidth="1" />
        <path d="M36 2 L44 6 L36 10" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
    </div>
  )
}

interface DiagramNodeProps {
  node: (typeof nodes)[number]
  index: number
  morphProgress: any
}

function DiagramNode({ node, index, morphProgress }: DiagramNodeProps) {
  const ref = useRef<HTMLDivElement>(null)
  const setPosition = useNodePositions((s) => s.setPosition)

  const opacity = useTransform(morphProgress, [0, 0.5], [1, 0])
  const scale = useTransform(morphProgress, [0, 0.5], [1, 0.95])
  const y = useTransform(morphProgress, [0, 0.5], [0, -8])

  const reportPosition = useCallback(() => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    setPosition(`node-${index}`, {
      x: rect.x + rect.width / 2,
      y: rect.y + rect.height / 2,
      width: rect.width,
      height: rect.height,
    })
  }, [index, setPosition])

  useEffect(() => {
    reportPosition()
    window.addEventListener("resize", reportPosition)
    window.addEventListener("scroll", reportPosition)
    return () => {
      window.removeEventListener("resize", reportPosition)
      window.removeEventListener("scroll", reportPosition)
    }
  }, [reportPosition])

  return (
    <motion.div
      ref={ref}
      className="flex flex-col items-center gap-3 px-2"
      style={{ opacity, scale, y }}
    >
      <div className="w-20 h-20 border border-border-primary rounded-[6px] flex items-center justify-center bg-bg-elevated text-text-primary">
        <node.Icon size={36} />
      </div>
      <span className="text-[15px] font-semibold text-text-primary tracking-[-0.01em]">
        {node.label}
      </span>
      <span className="text-[13px] text-text-secondary">
        {node.desc}
      </span>
    </motion.div>
  )
}

export function EngineDiagram() {
  const sectionRef = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  })

  const morphProgress = useTransform(scrollYProgress, [0.4, 0.7], [0, 1])
  const arrowOpacity = useTransform(morphProgress, [0, 0.3], [1, 0])

  return (
    <section ref={sectionRef}>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-16"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          How the engine works
        </motion.p>

        {/* Desktop: horizontal pipeline with morph */}
        <div className="hidden lg:flex items-stretch justify-between">
          {nodes.map((node, i) => (
            <div key={node.label} className="flex items-center">
              <DiagramNode node={node} index={i} morphProgress={morphProgress} />
              {i < nodes.length - 1 && (
                <motion.div style={{ opacity: arrowOpacity }}>
                  <Arrow />
                </motion.div>
              )}
            </div>
          ))}
        </div>

        {/* Tablet: 2x2 grid */}
        <div className="hidden md:grid md:grid-cols-2 gap-4 lg:hidden">
          {nodes.map((node, i) => (
            <motion.div
              key={node.label}
              className="flex items-center gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="w-10 h-10 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0 text-text-primary">
                <node.Icon size={20} />
              </div>
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {node.label}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {node.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical pipeline */}
        <div className="flex flex-col gap-3 md:hidden">
          {nodes.map((node, i) => (
            <motion.div
              key={node.label}
              className="flex items-center gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="w-8 h-8 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0 text-text-primary">
                <node.Icon size={16} />
              </div>
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {node.label}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {node.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
