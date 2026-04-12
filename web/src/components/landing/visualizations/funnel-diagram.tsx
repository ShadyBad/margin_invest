/**
 * FunnelDiagram -- Vertical funnel showing pipeline narrowing stages.
 *
 * 4 horizontal bars that narrow from top to bottom, connected by angled
 * connectors. Gradient fills, scroll-reveal animation, and terminal-card
 * design language.
 *
 * Used in: Pipeline section (Step 10).
 */

"use client"

import { useEffect, useRef, useState } from "react"

interface FunnelDiagramProps {
  universeCount: number
  eligibleCount: number
  scoredCount: number
  survivingCount: number
  className?: string
}

interface FunnelStage {
  label: string
  count: number
  widthPct: number
}

function formatCount(n: number): string {
  return n.toLocaleString("en-US")
}

export function FunnelDiagram({
  universeCount,
  eligibleCount,
  scoredCount,
  survivingCount,
  className,
}: FunnelDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [revealed, setRevealed] = useState(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true)
          observer.disconnect()
        }
      },
      { threshold: 0.3 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const stages: FunnelStage[] = [
    { label: "Universe", count: universeCount, widthPct: 100 },
    { label: "Eligible", count: eligibleCount, widthPct: 72 },
    { label: "Scored", count: scoredCount, widthPct: 48 },
    { label: "Survivors", count: survivingCount, widthPct: 30 },
  ]

  return (
    <div ref={containerRef} className={className}>
      <div className="flex flex-col items-center gap-0 w-full max-w-sm mx-auto">
        {stages.map((stage, i) => {
          const isLast = i === stages.length - 1

          return (
            <div key={stage.label} className="flex flex-col items-center w-full">
              {/* Row: label — bar — count */}
              <div className="flex items-center w-full gap-3">
                {/* Label (fixed left) */}
                <span
                  className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-tertiary whitespace-nowrap w-20 text-right shrink-0"
                  style={{
                    opacity: revealed ? 1 : 0,
                    transition: "opacity 400ms ease",
                    transitionDelay: `${i * 150 + 400}ms`,
                  }}
                >
                  {stage.label}
                </span>

                {/* Bar (scales by percentage) */}
                <div className="flex-1 flex">
                  <div
                    className="rounded-md transition-all duration-700 ease-out"
                    data-funnel-stage={stage.label}
                    style={{
                      width: revealed ? `${stage.widthPct}%` : "0%",
                      transitionDelay: `${i * 150}ms`,
                      height: 32,
                      background: `linear-gradient(135deg, color-mix(in srgb, var(--color-accent) ${90 - i * 18}%, transparent) 0%, color-mix(in srgb, var(--color-accent) ${60 - i * 12}%, transparent) 100%)`,
                      border: "1px solid color-mix(in srgb, var(--color-accent) 20%, transparent)",
                    }}
                  />
                </div>

                {/* Count (fixed right) */}
                <span
                  className="font-mono text-sm font-semibold text-text-primary whitespace-nowrap tabular-nums w-14 shrink-0"
                  style={{
                    opacity: revealed ? 1 : 0,
                    transition: "opacity 400ms ease",
                    transitionDelay: `${i * 150 + 500}ms`,
                  }}
                >
                  {formatCount(stage.count)}
                </span>
              </div>

              {/* Connector spacer */}
              {!isLast && <div className="h-2" />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
