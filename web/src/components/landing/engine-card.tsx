"use client"

import { motion, type MotionStyle } from "framer-motion"

interface EngineCardProps {
  title: string
  subtitle: string
  description: string
  style?: MotionStyle
}

export function EngineCard({ title, subtitle, description, style }: EngineCardProps) {
  return (
    <motion.div
      className="w-[320px] flex-shrink-0 terminal-card p-6 md:p-8"
      style={style}
    >
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-3">
        {subtitle}
      </p>
      <h3 className="font-display text-2xl md:text-3xl leading-tight text-text-primary mb-3">
        {title}
      </h3>
      <p className="text-sm text-text-secondary leading-relaxed">
        {description}
      </p>
    </motion.div>
  )
}
