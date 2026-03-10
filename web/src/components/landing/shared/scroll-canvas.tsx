"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
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
  const isMobile = useIsMobile()

  useEffect(() => {
    // On mobile, skip ScrollSmoother entirely
    if (isMobile) {
      setIsSmoothScrolling(false)
      setReady(true)
      return
    }

    let cancelled = false
    let smoother: { kill: () => void } | null = null

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

      if (!cancelled) {
        setReady(true)
      }
    }

    init().catch(() => {})

    return () => {
      cancelled = true
      smoother?.kill()
      setIsSmoothScrolling(false)
    }
  }, [isMobile])

  return (
    <ScrollCanvasContext.Provider value={{ ready, isSmoothScrolling }}>
      <div id="smooth-wrapper">
        <div id="smooth-content">
          {children}
        </div>
      </div>
    </ScrollCanvasContext.Provider>
  )
}
