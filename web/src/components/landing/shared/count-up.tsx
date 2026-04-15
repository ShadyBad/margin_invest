"use client"

import { useEffect, useRef, useState } from "react"

interface CountUpProps {
  /** Target value to count up to */
  value: number
  /** Duration of the count animation in seconds */
  duration?: number
  /** Format the number (e.g., add commas). Defaults to toLocaleString */
  format?: (n: number) => string
  /** Suffix to display after the number (e.g., "%", "+") */
  suffix?: string
  /** Prefix to display before the number (e.g., "$") */
  prefix?: string
  /** Additional className for the number span */
  className?: string
  /** ScrollTrigger start position */
  start?: string
}

function defaultFormat(n: number): string {
  return Math.round(n).toLocaleString("en-US")
}

export function CountUp({
  value,
  duration = 1.5,
  format = defaultFormat,
  suffix = "",
  prefix = "",
  className,
  start = "top 88%",
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const [display, setDisplay] = useState(format(0))
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!ref.current || hasAnimated.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(format(value))
      return
    }

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = ref.current
      if (!el) return

      const proxy = { val: 0 }

      trigger = ScrollTrigger.create({
        trigger: el,
        start,
        once: true,
        onEnter: () => {
          hasAnimated.current = true
          gsap.to(proxy, {
            val: value,
            duration,
            ease: "power2.out",
            onUpdate: () => setDisplay(format(proxy.val)),
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [value, duration, format, start])

  return (
    <span ref={ref} className={className}>
      {prefix}{display}{suffix}
    </span>
  )
}
