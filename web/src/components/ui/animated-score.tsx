"use client"

import { useRef, useEffect } from "react"
import { useInView, useMotionValue, animate } from "framer-motion"

interface AnimatedScoreProps {
  value: number
  className?: string
  duration?: number
}

export function AnimatedScore({ value, className = "", duration = 0.6 }: AnimatedScoreProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const motionValue = useMotionValue(0)

  useEffect(() => {
    if (!isInView) return
    const controls = animate(motionValue, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
    })
    return controls.stop
  }, [isInView, motionValue, value, duration])

  useEffect(() => {
    const unsubscribe = motionValue.on("change", (v) => {
      if (ref.current) ref.current.textContent = Math.round(v).toString()
    })
    return unsubscribe
  }, [motionValue])

  return (
    <span ref={ref} className={className} data-testid="animated-score">
      {Math.round(value)}
    </span>
  )
}
