"use client"

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react"
import { useIsMobile } from "@/hooks/use-media-query"

interface ScrollCanvasContextValue {
  ready: boolean
  isSmoothScrolling: boolean
}

const ScrollCanvasContext = createContext<ScrollCanvasContextValue>({
  ready: false,
  isSmoothScrolling: false,
})

export function useScrollCanvas(): ScrollCanvasContextValue {
  return useContext(ScrollCanvasContext)
}

interface ScrollCanvasProps {
  children: ReactNode
}

export function ScrollCanvas({ children }: ScrollCanvasProps) {
  const [ready, setReady] = useState(false)
  const [isSmoothScrolling, setIsSmoothScrolling] = useState(false)
  const gradientRef = useRef<HTMLDivElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const isMobile = useIsMobile()

  useEffect(() => {
    // On mobile, skip ScrollSmoother entirely — just mark ready with static layers
    if (isMobile) {
      setIsSmoothScrolling(false)
      setReady(true)
      return
    }

    let cancelled = false
    let smoother: { kill: () => void } | null = null
    const scrollTriggers: Array<{ kill: () => void }> = []

    async function init() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      const { default: ScrollSmoother } = await import("gsap/ScrollSmoother")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger, ScrollSmoother)

      smoother = ScrollSmoother.create({
        wrapper: "#smooth-wrapper",
        content: "#smooth-content",
        smooth: 1.2,
        effects: true,
        normalizeScroll: true,
      })

      setIsSmoothScrolling(true)

      // Gradient breathing timeline scrubbed by scroll
      if (gradientRef.current) {
        const gradientTl = gsap.timeline({
          scrollTrigger: {
            trigger: "#smooth-content",
            start: "top top",
            end: "bottom bottom",
            scrub: true,
          },
        })

        // 0-25%: emerald glow centered high (50% 30%), opacity 0.10 (initial state)
        // 25-55%: glow migrates to 60% 50%, opacity 0.12
        gradientTl.to(
          gradientRef.current,
          {
            "--glow-x": "60%",
            "--glow-y": "50%",
            "--glow-opacity": "0.12",
            duration: 0.30, // 25% to 55% = 30% of total
          },
          0.25 // start at 25%
        )

        // 55-80%: warm shift — color changes to warm muted, opacity 0.08
        gradientTl.to(
          gradientRef.current,
          {
            "--glow-color": "rgba(201, 150, 59, 0.15)",
            "--glow-opacity": "0.08",
            duration: 0.25, // 55% to 80% = 25% of total
          },
          0.55 // start at 55%
        )

        // 80-100%: cools back, opacity 0.04
        gradientTl.to(
          gradientRef.current,
          {
            "--glow-color": "rgba(26, 122, 90, 0.10)",
            "--glow-opacity": "0.04",
            duration: 0.20, // 80% to 100% = 20% of total
          },
          0.80 // start at 80%
        )

        const gradientSt = gradientTl.scrollTrigger
        if (gradientSt) scrollTriggers.push(gradientSt as unknown as { kill: () => void })
      }

      // Grid continuity timeline scrubbed by scroll
      if (gridRef.current) {
        const gridTl = gsap.timeline({
          scrollTrigger: {
            trigger: "#smooth-content",
            start: "top top",
            end: "bottom bottom",
            scrub: true,
          },
        })

        // 0-25%: 64px grid, opacity 0.04 (initial state)
        // 25-55%: 48px grid, opacity 0.04
        gridTl.to(
          gridRef.current,
          {
            backgroundSize: "48px 48px",
            duration: 0.30,
          },
          0.25
        )

        // 55-80%: opacity 0.01
        gridTl.to(
          gridRef.current,
          {
            opacity: 0.01,
            duration: 0.25,
          },
          0.55
        )

        // 80-100%: opacity 0.02
        gridTl.to(
          gridRef.current,
          {
            opacity: 0.02,
            duration: 0.20,
          },
          0.80
        )

        const gridSt = gridTl.scrollTrigger
        if (gridSt) scrollTriggers.push(gridSt as unknown as { kill: () => void })
      }

      if (!cancelled) {
        setReady(true)
      }
    }

    init().catch(() => {})

    return () => {
      cancelled = true
      scrollTriggers.forEach((st) => st.kill())
      smoother?.kill()
      setIsSmoothScrolling(false)
    }
  }, [isMobile])

  return (
    <ScrollCanvasContext.Provider value={{ ready, isSmoothScrolling }}>
      {/* Persistent background layers — fixed position, outside scroll flow */}
      <div
        ref={gradientRef}
        data-testid="canvas-gradient"
        className="pointer-events-none fixed inset-0"
        style={{
          "--glow-x": "50%",
          "--glow-y": "30%",
          "--glow-color": "rgba(26, 122, 90, 0.10)",
          "--glow-opacity": "0.10",
          background:
            "radial-gradient(ellipse 60% 50% at var(--glow-x) var(--glow-y), var(--glow-color) 0%, transparent 65%)",
          opacity: "var(--glow-opacity)",
        } as React.CSSProperties}
      />

      <div
        ref={gridRef}
        data-testid="canvas-grid"
        className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 0.04,
        }}
      />

      <div
        data-testid="canvas-noise"
        className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "url('/noise.svg')",
          backgroundRepeat: "repeat",
          opacity: 0.4,
        }}
      />

      {/* ScrollSmoother DOM structure */}
      <div id="smooth-wrapper">
        <div id="smooth-content">
          {children}
        </div>
      </div>
    </ScrollCanvasContext.Provider>
  )
}
