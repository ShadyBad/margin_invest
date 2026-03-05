"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import type { CandidateCard } from "./types"
import { ENGINE_VERSION } from "./candidate-data"
import { MicroMetadata } from "./micro-metadata"

interface HeroCandidateCardProps {
  candidates: CandidateCard[]
  universeSize?: number
  eligibleCount?: number
}

const ROTATION_INTERVAL = 7000
const FADE_OUT_MS = 150
const FADE_IN_MS = 200
const SWIPE_THRESHOLD = 50
const EASING = "cubic-bezier(0.4, 0, 0.2, 1)"

interface FactorBar {
  label: string
  value: number
}

function getFactors(candidate: CandidateCard): FactorBar[] {
  return [
    { label: "Valuation", value: candidate.value_percentile },
    { label: "Quality", value: candidate.quality_percentile },
    { label: "Momentum", value: candidate.momentum_percentile },
    { label: "Sentiment", value: candidate.sentiment_percentile },
    { label: "Growth", value: candidate.growth_percentile },
  ].filter((f) => f.value > 0)
}

function formatTime(): string {
  const now = new Date()
  const hours = now.getHours()
  const minutes = now.getMinutes().toString().padStart(2, "0")
  const period = hours >= 12 ? "PM" : "AM"
  const h12 = hours % 12 || 12
  return `${h12}:${minutes} ${period} EST`
}

function formatNumber(n: number): string {
  return n.toLocaleString("en-US")
}

function formatMoS(mos: number): string {
  return `${(mos * 100).toFixed(1)}%`
}

function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

function getFactorBarColor(value: number): string {
  if (value >= 75) return "var(--color-bullish)"
  if (value >= 50) return "var(--color-accent)"
  return "var(--color-text-tertiary)"
}

function ScoreRing({ score }: { score: number }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(score, 100) / 100
  const dashOffset = circumference * (1 - progress)

  return (
    <div className="relative flex items-center justify-center" style={{ width: 72, height: 72 }}>
      <svg width={72} height={72} viewBox="0 0 72 72" className="rotate-[-90deg]">
        {/* Track */}
        <circle
          cx={36}
          cy={36}
          r={radius}
          fill="none"
          stroke="var(--color-border-subtle)"
          strokeWidth={3}
        />
        {/* Progress */}
        <circle
          cx={36}
          cy={36}
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </svg>
      <span className="absolute font-mono text-2xl font-bold text-text-primary">
        {Math.round(score)}
      </span>
    </div>
  )
}

export function HeroCandidateCard({
  candidates,
  universeSize,
  eligibleCount,
}: HeroCandidateCardProps) {
  const [activeIndex, setActiveIndex] = useState(0)
  const [opacity, setOpacity] = useState(1)
  const [barWidths, setBarWidths] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const touchStartRef = useRef<number | null>(null)
  const isTouchDevice = useRef(false)

  const candidate = candidates[activeIndex]
  const factors = getFactors(candidate)
  const hasMultiple = candidates.length > 1

  const goToIndex = useCallback(
    (next: number) => {
      // Fade out
      setOpacity(0)
      setBarWidths(false)
      setTimeout(() => {
        setActiveIndex(next)
        // Fade in after data swap
        requestAnimationFrame(() => {
          setOpacity(1)
          setBarWidths(true)
        })
      }, FADE_OUT_MS)
    },
    []
  )

  const goNext = useCallback(() => {
    const next = (activeIndex + 1) % candidates.length
    goToIndex(next)
  }, [activeIndex, candidates.length, goToIndex])

  const goPrev = useCallback(() => {
    const next = (activeIndex - 1 + candidates.length) % candidates.length
    goToIndex(next)
  }, [activeIndex, candidates.length, goToIndex])

  // Detect touch device
  useEffect(() => {
    if (typeof window !== "undefined" && "ontouchstart" in window) {
      isTouchDevice.current = true
    }
  }, [])

  // Auto-rotation
  useEffect(() => {
    if (!hasMultiple || isTouchDevice.current) return

    intervalRef.current = setInterval(goNext, ROTATION_INTERVAL)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [hasMultiple, goNext])

  // Touch/swipe handling
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartRef.current = e.touches[0].clientX
  }, [])

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (touchStartRef.current === null || !hasMultiple) return
      const diff = e.changedTouches[0].clientX - touchStartRef.current
      if (Math.abs(diff) >= SWIPE_THRESHOLD) {
        if (diff < 0) {
          goNext()
        } else {
          goPrev()
        }
      }
      touchStartRef.current = null
    },
    [hasMultiple, goNext, goPrev]
  )

  // Trigger bar animation on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- triggers CSS transition after mount for animation
    setBarWidths(true)
  }, [])

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header metadata bar */}
      <div className="flex items-center justify-between mb-3 px-1">
        <MicroMetadata text="Live Engine Output — Today" />
        <MicroMetadata text={`Updated ${formatTime()} · Engine ${ENGINE_VERSION}`} />
      </div>

      {/* Card */}
      <div
        className="relative overflow-hidden rounded-xl bg-bg-elevated"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        style={{
          opacity,
          transition: `opacity ${opacity === 0 ? FADE_OUT_MS : FADE_IN_MS}ms ${EASING}`,
          border: "1px solid color-mix(in srgb, var(--color-accent) 35%, var(--color-border-subtle))",
          boxShadow: "0 0 40px color-mix(in srgb, var(--color-accent) 12%, transparent), 0 8px 32px rgba(0,0,0,0.4), 0 1px 0 color-mix(in srgb, var(--color-accent) 30%, transparent) inset",
        }}
      >
        {/* 3px gradient top bar */}
        <div
          className="w-full"
          style={{
            height: "3px",
            background: "linear-gradient(to right, var(--color-accent), transparent)",
          }}
        />

        <div className="p-6 md:p-8">
          {/* Ticker + Sector + ScoreRing */}
          <div className="flex items-start justify-between mb-5">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xl font-bold text-text-primary">
                  {candidate.ticker}
                </span>
                <span className="text-[10px] uppercase tracking-widest text-text-tertiary px-2 py-0.5 rounded border border-border-subtle">
                  {candidate.sector}
                </span>
              </div>
              <span className="text-sm text-text-secondary">{candidate.name}</span>
            </div>

            {/* Composite Score Ring */}
            <div className="text-center">
              <ScoreRing score={candidate.score} />
              <div className="text-[10px] uppercase tracking-widest text-text-tertiary mt-1">
                Composite Score
              </div>
            </div>
          </div>

          {/* Price / Target / MoS — 3-column inset row */}
          <div
            className="grid grid-cols-3 gap-3 mb-5 p-3"
            style={{
              backgroundColor: "var(--color-bg-subtle)",
              borderRadius: "8px",
            }}
          >
            <div>
              <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                Price
              </div>
              <div className="font-mono text-sm font-semibold text-text-primary">
                {formatPrice(candidate.actual_price)}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                Target
              </div>
              <div className="font-mono text-sm font-semibold text-accent">
                {formatPrice(candidate.buy_price)}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
                Margin of Safety
              </div>
              <div className="font-mono text-sm font-semibold text-text-primary">
                {formatMoS(candidate.margin_of_safety)}
              </div>
            </div>
          </div>

          {/* Factor Bars */}
          <div className="space-y-2.5 mb-4">
            {factors.map((factor) => (
              <div key={factor.label} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary w-20 shrink-0">
                  {factor.label}
                </span>
                <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: barWidths ? `${factor.value}%` : "0%",
                      backgroundColor: getFactorBarColor(factor.value),
                      transition: `width 700ms ${EASING}`,
                    }}
                  />
                </div>
                <span className="font-mono text-xs text-text-secondary w-8 text-right">
                  {Math.round(factor.value)}
                </span>
              </div>
            ))}
          </div>

          {/* Bottom metadata */}
          {(universeSize || eligibleCount) && (
            <div className="pt-3 border-t border-border-subtle">
              <MicroMetadata
                text={[
                  universeSize ? `Universe: ${formatNumber(universeSize)}` : null,
                  eligibleCount ? `Eligible: ${formatNumber(eligibleCount)}` : null,
                  `Filters: ${candidate.filters_passed}/${candidate.filters_total}`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              />
            </div>
          )}
        </div>
      </div>

      {/* Pill dot indicators (mobile only) */}
      {hasMultiple && (
        <div className="flex justify-center gap-1.5 mt-3 md:hidden">
          {candidates.map((_, i) => (
            <button
              key={i}
              onClick={() => goToIndex(i)}
              aria-label={`Go to candidate ${i + 1}`}
              className="rounded-full transition-all duration-200"
              style={{
                width: i === activeIndex ? 16 : 6,
                height: 6,
                backgroundColor: i === activeIndex
                  ? "var(--color-accent)"
                  : "var(--color-border-subtle)",
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
