/**
 * AnimatedCounter -- Animates from 0 to a target number on mount.
 *
 * Uses requestAnimationFrame with easeOutQuart easing for natural deceleration.
 * Formats the displayed number with locale separators (e.g., 3,056).
 *
 * Used in: Evidence Panel (Step 9), Pipeline (Step 10).
 */

"use client"

import { useEffect, useReducer } from "react"

interface AnimatedCounterProps {
  target: number
  duration?: number // ms, default 1000
  separator?: string // default ","
  className?: string
}

/** easeOutQuart: fast start, slow approach to 1 */
function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4)
}

function formatNumber(value: number, separator: string): string {
  if (separator === ",") {
    return value.toLocaleString("en-US")
  }
  return value.toLocaleString("en-US").replace(/,/g, separator)
}

export function AnimatedCounter({
  target,
  duration = 1000,
  separator = ",",
  className,
}: AnimatedCounterProps) {
  // useReducer avoids the "setState in effect" lint warning since
  // dispatch is stable and we call it from a rAF callback (not effect body).
  const [displayValue, setDisplay] = useReducer(
    (_prev: number, next: number) => next,
    0,
  )

  useEffect(() => {
    if (target === 0) {
      return
    }

    let startTime: number | null = null
    let raf: number

    function step(timestamp: number) {
      if (startTime === null) {
        startTime = timestamp
      }

      const elapsed = timestamp - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = easeOutQuart(progress)
      const current = Math.round(eased * target)

      setDisplay(current)

      if (progress < 1) {
        raf = requestAnimationFrame(step)
      } else {
        setDisplay(target)
      }
    }

    raf = requestAnimationFrame(step)

    return () => {
      cancelAnimationFrame(raf)
    }
  }, [target, duration])

  return (
    <span className={className}>{formatNumber(displayValue, separator)}</span>
  )
}
