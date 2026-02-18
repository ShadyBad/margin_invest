"use client"

import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion"
import { GlassSurface } from "../ui/glass-surface"

interface FlowCardProps {
  title: string
  subtitle: string
  children: ReactNode
}

export function FlowCard({ title, subtitle, children }: FlowCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })

  const opacity = useTransform(
    scrollYProgress,
    [0, 0.3, 0.5, 0.7, 1],
    [0.15, 0.6, 1, 0.6, 0.15],
  )

  const blur = useTransform(
    scrollYProgress,
    [0, 0.3, 0.5, 0.7, 1],
    prefersReducedMotion ? [0, 0, 0, 0, 0] : [4, 1.5, 0, 1.5, 4],
  )

  const filterBlur = useTransform(blur, (v) => `blur(${v}px)`)

  return (
    <motion.div
      ref={ref}
      data-flow-card
      className="w-full md:w-[320px] flex-shrink-0"
      style={{ opacity, filter: filterBlur }}
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
