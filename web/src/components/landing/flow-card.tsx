"use client"

import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform, type MotionStyle } from "framer-motion"
import { GlassSurface } from "../ui/glass-surface"

interface FlowCardProps {
  title: string
  subtitle: string
  children: ReactNode
  /** When provided, uses these motion styles instead of self-tracking scroll position */
  motionStyle?: MotionStyle
}

export function FlowCard({ title, subtitle, children, motionStyle }: FlowCardProps) {
  const ref = useRef<HTMLDivElement>(null)

  // Self-tracking mode: used in mobile layout where cards scroll vertically
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })

  const selfOpacity = useTransform(
    scrollYProgress,
    [0, 0.3, 0.5, 0.7, 1],
    [0.15, 0.6, 1, 0.6, 0.15],
  )

  // Use parent-provided motion styles (desktop) or self-tracking (mobile)
  const style: MotionStyle = motionStyle ?? { opacity: selfOpacity }

  return (
    <motion.div
      ref={ref}
      data-flow-card
      className="w-full md:w-[320px] flex-shrink-0"
      style={style}
    >
      <GlassSurface className="p-6 md:p-8 h-full">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-text-tertiary)] mb-3">
          {subtitle}
        </p>
        <h3 className="font-display text-2xl md:text-3xl leading-tight text-[var(--color-text-primary)] mb-4">
          {title}
        </h3>
        {children}
      </GlassSurface>
    </motion.div>
  )
}
