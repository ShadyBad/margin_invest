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
  ]
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
        className="terminal-card p-6 md:p-8 border border-accent/20"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        style={{
          opacity,
          transition: `opacity ${opacity === 0 ? FADE_OUT_MS : FADE_IN_MS}ms ${EASING}`,
        }}
      >
        {/* Ticker + Sector */}
        <div className="flex items-center gap-3 mb-4">
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
        </div>

        {/* Price Grid */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
              Current Price
            </div>
            <div className="font-mono text-lg font-semibold text-text-primary">
              {formatPrice(candidate.actual_price)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
              Target Price
            </div>
            <div className="font-mono text-lg font-semibold text-accent">
              {formatPrice(candidate.buy_price)}
            </div>
          </div>
        </div>

        {/* Margin of Safety */}
        <div className="mb-4">
          <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">
            Margin of Safety
          </div>
          <div className="font-mono text-lg font-semibold text-text-primary">
            {formatMoS(candidate.margin_of_safety)}
          </div>
        </div>

        {/* Conviction Score — largest element */}
        <div className="border-y border-border-subtle py-4 my-4 text-center">
          <div className="text-[10px] uppercase tracking-widest text-text-tertiary mb-2">
            Conviction Score
          </div>
          <div className="font-mono text-5xl font-bold text-text-primary">
            {candidate.composite_percentile}
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
                  className="h-full bg-accent rounded-full"
                  style={{
                    width: barWidths ? `${factor.value}%` : "0%",
                    transition: `width 700ms ${EASING}`,
                  }}
                />
              </div>
              <span className="font-mono text-xs text-text-secondary w-8 text-right">
                {factor.value}
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

      {/* Dot indicators (mobile only) */}
      {hasMultiple && (
        <div className="flex justify-center gap-2 mt-3 md:hidden">
          {candidates.map((_, i) => (
            <button
              key={i}
              onClick={() => goToIndex(i)}
              aria-label={`Go to candidate ${i + 1}`}
              className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
                i === activeIndex
                  ? "bg-accent"
                  : "bg-border-subtle"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  )
}
