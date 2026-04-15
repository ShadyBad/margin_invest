"use client"

import { useEffect, useRef, type CSSProperties } from "react"

interface TextRevealProps {
  /** The text to reveal */
  text: string
  /** Split mode: reveal by word or by line */
  mode?: "word" | "line"
  /** Animation effect for each unit */
  effect?: "fade-up" | "blur-up" | "clip-up"
  /** Base delay before animation starts */
  delay?: number
  /** Stagger delay between each word/line */
  stagger?: number
  /** Duration per word/line */
  duration?: number
  /** ScrollTrigger start (if omitted, plays on mount) */
  scrollStart?: string
  /** HTML tag */
  as?: "h1" | "h2" | "h3" | "p" | "span" | "div"
  /** Class applied to the outer wrapper */
  className?: string
  /** Style applied to the outer wrapper */
  style?: CSSProperties
  /** Class applied to each word/line span */
  unitClassName?: string
}

export function TextReveal({
  text,
  mode = "word",
  effect = "blur-up",
  delay = 0,
  stagger = 0.06,
  duration = 0.5,
  scrollStart,
  as: Tag = "span",
  className,
  style,
  unitClassName,
}: TextRevealProps) {
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!ref.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // Show everything immediately
      const units = ref.current.querySelectorAll("[data-reveal-unit]")
      units.forEach((u) => {
        const el = u as HTMLElement
        el.style.opacity = "1"
        el.style.transform = "none"
        el.style.filter = "none"
        el.style.clipPath = "none"
      })
      return
    }

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default

      const el = ref.current
      if (!el) return

      const units = el.querySelectorAll("[data-reveal-unit]")
      if (units.length === 0) return

      // Set initial state based on effect
      const from: Record<string, number | string> = { opacity: 0 }
      const to: Record<string, number | string> = { opacity: 1 }

      if (effect === "fade-up") {
        from.y = 16
        to.y = 0
      } else if (effect === "blur-up") {
        from.y = 12
        from.filter = "blur(6px)"
        to.y = 0
        to.filter = "blur(0px)"
      } else if (effect === "clip-up") {
        from.clipPath = "inset(100% 0 0 0)"
        to.clipPath = "inset(0% 0 0 0)"
      }

      gsap.set(units, from)

      const doAnimate = () => {
        gsap.to(units, {
          ...to,
          duration,
          stagger,
          delay,
          ease: "power2.out",
        })
      }

      if (scrollStart) {
        const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
        if (cancelled) return
        gsap.registerPlugin(ScrollTrigger)

        trigger = ScrollTrigger.create({
          trigger: el,
          start: scrollStart,
          once: true,
          onEnter: doAnimate,
        })
      } else {
        doAnimate()
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [effect, delay, stagger, duration, scrollStart])

  const units = mode === "word" ? text.split(" ") : text.split("\n")

  return (
    // @ts-expect-error -- dynamic tag with ref
    <Tag ref={ref} className={className} style={style}>
      {units.map((unit, i) => (
        <span
          key={i}
          data-reveal-unit
          className={unitClassName}
          style={{
            display: "inline-block",
            whiteSpace: mode === "word" ? "pre" : undefined,
          }}
        >
          {unit}{mode === "word" && i < units.length - 1 ? " " : ""}
        </span>
      ))}
    </Tag>
  )
}
