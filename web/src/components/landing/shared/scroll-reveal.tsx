"use client"

import { useEffect, useRef, type ReactNode, type CSSProperties } from "react"

type RevealEffect = "fade-up" | "fade-in" | "blur-up" | "slide-left" | "slide-right" | "scale-up"

interface ScrollRevealProps {
  children: ReactNode
  /** Animation effect to apply */
  effect?: RevealEffect
  /** Delay in seconds before this element animates (useful for staggering siblings) */
  delay?: number
  /** Duration of the animation in seconds */
  duration?: number
  /** ScrollTrigger start position (default: "top 88%") */
  start?: string
  /** If true, animation progress is linked to scroll position instead of one-shot */
  scrub?: boolean | number
  /** Distance for translate effects in px */
  distance?: number
  /** Additional className */
  className?: string
  /** Additional inline styles */
  style?: CSSProperties
  /** Stagger children with data-reveal-item attribute instead of animating the container */
  stagger?: number
  /** HTML tag to render (default: div) */
  as?: keyof HTMLElementTagNameMap
}

const EFFECT_FROM: Record<RevealEffect, Record<string, number | string>> = {
  "fade-up": { opacity: 0, y: 32 },
  "fade-in": { opacity: 0 },
  "blur-up": { opacity: 0, y: 24, filter: "blur(8px)" },
  "slide-left": { opacity: 0, x: -48 },
  "slide-right": { opacity: 0, x: 48 },
  "scale-up": { opacity: 0, scale: 0.92 },
}

const EFFECT_TO: Record<RevealEffect, Record<string, number | string>> = {
  "fade-up": { opacity: 1, y: 0 },
  "fade-in": { opacity: 1 },
  "blur-up": { opacity: 1, y: 0, filter: "blur(0px)" },
  "slide-left": { opacity: 1, x: 0 },
  "slide-right": { opacity: 1, x: 0 },
  "scale-up": { opacity: 1, scale: 1 },
}

export function ScrollReveal({
  children,
  effect = "blur-up",
  delay = 0,
  duration = 0.7,
  start = "top 88%",
  scrub = false,
  distance,
  className,
  style,
  stagger,
  as: Tag = "div",
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

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

      const from = { ...EFFECT_FROM[effect] }
      const to = { ...EFFECT_TO[effect] }

      // Allow custom distance override
      if (distance !== undefined) {
        if ("y" in from) from.y = distance
        if ("x" in from) from.x = effect.includes("left") ? -distance : distance
      }

      if (stagger != null) {
        // Stagger mode: animate children with data-reveal-item
        const items = el.querySelectorAll("[data-reveal-item]")
        if (items.length === 0) return

        gsap.set(items, from)

        if (scrub) {
          gsap.to(items, {
            ...to,
            duration,
            stagger,
            ease: "none",
            scrollTrigger: {
              trigger: el,
              start,
              end: "bottom 20%",
              scrub: typeof scrub === "number" ? scrub : 1,
            },
          })
        } else {
          trigger = ScrollTrigger.create({
            trigger: el,
            start,
            once: true,
            onEnter: () => {
              gsap.to(items, {
                ...to,
                duration,
                stagger,
                delay,
                ease: "power2.out",
              })
            },
          })
        }
      } else {
        // Single element mode
        gsap.set(el, from)

        if (scrub) {
          gsap.to(el, {
            ...to,
            duration,
            ease: "none",
            scrollTrigger: {
              trigger: el,
              start,
              end: "bottom 20%",
              scrub: typeof scrub === "number" ? scrub : 1,
            },
          })
        } else {
          trigger = ScrollTrigger.create({
            trigger: el,
            start,
            once: true,
            onEnter: () => {
              gsap.to(el, {
                ...to,
                duration,
                delay,
                ease: "power2.out",
              })
            },
          })
        }
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [effect, delay, duration, start, scrub, distance, stagger])

  return (
    // @ts-expect-error -- dynamic tag with ref
    <Tag ref={ref} className={className} style={style}>
      {children}
    </Tag>
  )
}
