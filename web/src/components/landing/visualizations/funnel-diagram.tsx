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
      <div className="flex flex-col items-center gap-0">
        {stages.map((stage, i) => {
          const isLast = i === stages.length - 1

          return (
            <div key={stage.label} className="flex flex-col items-center w-full">
              {/* Bar */}
              <div
                className="relative flex items-center justify-between rounded-lg overflow-hidden transition-all duration-700 ease-out"
                data-funnel-stage={stage.label}
                style={{
                  width: revealed ? `${stage.widthPct}%` : "0%",
                  transitionDelay: `${i * 150}ms`,
                  minHeight: 44,
                  background: `linear-gradient(135deg, color-mix(in srgb, var(--color-accent) ${90 - i * 18}%, transparent) 0%, color-mix(in srgb, var(--color-accent) ${60 - i * 12}%, transparent) 100%)`,
                  border: "1px solid color-mix(in srgb, var(--color-accent) 20%, transparent)",
                }}
              >
                {/* Label */}
                <span
                  className="pl-4 font-mono text-[10px] uppercase tracking-[0.14em] text-text-primary whitespace-nowrap"
                  style={{
                    opacity: revealed ? 1 : 0,
                    transition: "opacity 400ms ease",
                    transitionDelay: `${i * 150 + 400}ms`,
                  }}
                >
                  {stage.label}
                </span>

                {/* Count */}
                <span
                  className="pr-4 font-mono text-sm font-semibold text-text-primary whitespace-nowrap tabular-nums"
                  style={{
                    opacity: revealed ? 1 : 0,
                    transition: "opacity 400ms ease",
                    transitionDelay: `${i * 150 + 500}ms`,
                  }}
                >
                  {formatCount(stage.count)}
                </span>
              </div>

              {/* Connector */}
              {!isLast && (
                <div
                  className="h-3 border-l border-r border-accent/10"
                  style={{
                    width: `${(stage.widthPct + stages[i + 1].widthPct) / 2}%`,
                    opacity: revealed ? 1 : 0,
                    transition: "opacity 300ms ease",
                    transitionDelay: `${i * 150 + 300}ms`,
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
