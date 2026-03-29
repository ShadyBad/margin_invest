"use client"

import { useEffect, useRef } from "react"

export interface FactorSignatureProps {
  factors: {
    quality: number | null
    value: number | null
    momentum: number | null
    sentiment: number | null
    growth: number | null
  }
  variant: "full" | "compact" | "mini" | "inline"
  className?: string
}

const FACTOR_CONFIG = [
  { key: "quality" as const, label: "QUALITY", abbrev: "Q", color: "#10B981" },
  { key: "value" as const, label: "VALUE", abbrev: "V", color: "#3BA5D0" },
  { key: "momentum" as const, label: "MOMENTUM", abbrev: "M", color: "#1A7A5A" },
  { key: "sentiment" as const, label: "SENTIMENT", abbrev: "S", color: "#C9A84C" },
  { key: "growth" as const, label: "GROWTH", abbrev: "G", color: "#22C55E" },
] as const

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** Dimensions and visibility per variant */
const VARIANT_SPEC = {
  full: {
    width: 340,
    height: 160,
    showLabels: "full" as const,
    showValues: true,
    showFill: true,
    trackSpacing: 32,
  },
  compact: {
    width: 260,
    height: 110,
    showLabels: "abbrev" as const,
    showValues: true,
    showFill: true,
    trackSpacing: 22,
  },
  mini: {
    width: 160,
    height: 50,
    showLabels: false as const,
    showValues: false,
    showFill: true,
    trackSpacing: 10,
  },
  inline: {
    width: 80,
    height: 10,
    showLabels: false as const,
    showValues: false,
    showFill: false,
    trackSpacing: 0,
  },
} as const

export function FactorSignature({
  factors,
  variant,
  className,
}: FactorSignatureProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const animatedRef = useRef(false)

  const spec = VARIANT_SPEC[variant]

  const visibleFactors = FACTOR_CONFIG.filter(
    (f) => factors[f.key] !== null && factors[f.key] !== undefined,
  )

  // Animation effect for track-based variants
  useEffect(() => {
    if (variant === "inline") return
    if (animatedRef.current || !svgRef.current) return
    animatedRef.current = true

    const prefersReduced =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReduced) return

    async function runAnimation() {
      const gsapModule = await import("gsap")
      const gsap = gsapModule.default
      const svg = svgRef.current
      if (!svg) return

      const dots = svg.querySelectorAll("[data-marker-dot]")
      const fills = svg.querySelectorAll("[data-fill-bar]")
      const line = svg.querySelector("[data-connecting-line]")

      gsap.set(dots, { opacity: 0, scale: 0 })
      gsap.set(fills, { scaleX: 0, transformOrigin: "left center" })
      if (line) gsap.set(line, { opacity: 0 })

      dots.forEach((dot, i) => {
        gsap.to(dot, {
          opacity: 1,
          scale: 1,
          duration: 0.3,
          delay: i * 0.08,
          ease: "back.out(2)",
        })
      })
      fills.forEach((fill, i) => {
        gsap.to(fill, {
          scaleX: 1,
          duration: 0.4,
          delay: i * 0.08,
          ease: "power2.out",
        })
      })
      if (line) {
        gsap.to(line, {
          opacity: 1,
          duration: 0.3,
          delay: dots.length * 0.08 + 0.1,
        })
      }
    }

    runAnimation().catch(() => {})
  }, [variant])

  // Inline variant: render as a simple row of dots
  if (variant === "inline") {
    const inlineWidth =
      visibleFactors.length > 1
        ? spec.width
        : visibleFactors.length === 1
          ? 10
          : 0
    return (
      <svg
        ref={svgRef}
        viewBox={`0 0 ${inlineWidth || spec.width} ${spec.height}`}
        className={className}
        width={inlineWidth || spec.width}
        height={spec.height}
        role="img"
        aria-label="Factor signature"
      >
        {visibleFactors.map((factor, i) => {
          const value = factors[factor.key]!
          const cx =
            visibleFactors.length > 1
              ? (i / (visibleFactors.length - 1)) * (inlineWidth - 10) + 5
              : inlineWidth / 2
          const cy = spec.height / 2
          const clamped = clamp(Math.round(value), 0, 100)
          const dotOpacity =
            clamped >= 80 ? 1 : clamped >= 60 ? 0.7 : clamped >= 40 ? 0.5 : 0.3
          return (
            <circle
              key={factor.key}
              data-marker-dot
              cx={cx}
              cy={cy}
              r={3}
              fill={factor.color}
              opacity={dotOpacity}
            />
          )
        })}
      </svg>
    )
  }

  // Track-based variants (full, compact, mini)
  const labelWidth =
    spec.showLabels === "full" ? 80 : spec.showLabels === "abbrev" ? 20 : 0
  const valueWidth = spec.showValues ? 30 : 0
  const trackLeft = labelWidth + (labelWidth > 0 ? 8 : 0)
  const trackRight = spec.width - valueWidth - (valueWidth > 0 ? 8 : 0)
  const trackWidth = trackRight - trackLeft
  const topPadding = variant === "mini" ? 5 : 10
  const dynamicHeight =
    topPadding +
    Math.max(0, visibleFactors.length - 1) * spec.trackSpacing +
    topPadding
  const polylinePoints: string[] = []

  const trackElements = visibleFactors.map((factor, i) => {
    const value = factors[factor.key]!
    const y = topPadding + i * spec.trackSpacing
    const clamped = clamp(Math.round(value), 0, 100)
    const dotX = trackLeft + (clamped / 100) * trackWidth

    polylinePoints.push(`${dotX},${y}`)

    return (
      <g key={factor.key}>
        {/* Track line */}
        <line
          data-track
          x1={trackLeft}
          y1={y}
          x2={trackRight}
          y2={y}
          stroke="rgba(237,233,227,0.06)"
          strokeWidth={1}
        />

        {/* Fill bar */}
        {spec.showFill && (
          <rect
            data-fill-bar
            x={trackLeft}
            y={y - 4}
            width={(clamped / 100) * trackWidth}
            height={8}
            rx={1}
            fill={factor.color}
            opacity={0.12}
          />
        )}

        {/* Marker dot */}
        <circle
          data-marker-dot
          cx={dotX}
          cy={y}
          r={variant === "mini" ? 2.5 : 3.5}
          fill={factor.color}
        />

        {/* Label */}
        {spec.showLabels && (
          <text
            x={0}
            y={y}
            dy="0.35em"
            fill="rgba(237,233,227,0.35)"
            fontSize={9}
            fontFamily="var(--font-geist-mono), monospace"
          >
            {spec.showLabels === "full" ? factor.label : factor.abbrev}
          </text>
        )}

        {/* Percentile value */}
        {spec.showValues && (
          <text
            x={spec.width}
            y={y}
            dy="0.35em"
            textAnchor="end"
            fill="rgba(237,233,227,0.5)"
            fontSize={10}
            fontFamily="var(--font-geist-mono), monospace"
          >
            {clamped}
          </text>
        )}
      </g>
    )
  })

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${spec.width} ${dynamicHeight}`}
      className={className}
      width={spec.width}
      height={dynamicHeight}
      role="img"
      aria-label="Factor signature"
    >
      {trackElements}

      {/* Connecting polyline */}
      {polylinePoints.length >= 2 && (
        <polyline
          data-connecting-line
          points={polylinePoints.join(" ")}
          fill="none"
          stroke="rgba(237,233,227,0.12)"
          strokeWidth={1.5}
        />
      )}
    </svg>
  )
}
