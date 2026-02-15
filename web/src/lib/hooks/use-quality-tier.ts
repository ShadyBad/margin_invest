"use client"

import { useMemo } from "react"

export type QualityTier = "high" | "medium" | "low"

interface QualityTierResult {
  tier: QualityTier
  dpr: number
  enableWebGL: boolean
}

function computeQualityTier(): QualityTierResult {
  if (typeof window === "undefined") {
    return { tier: "low", dpr: 1, enableWebGL: false }
  }

  const width = window.innerWidth
  const cores = navigator.hardwareConcurrency || 4

  if (width < 768) {
    return { tier: "low", dpr: 1, enableWebGL: false }
  } else if (width < 1024 || cores < 4) {
    return { tier: "medium", dpr: 1, enableWebGL: true }
  } else {
    return { tier: "high", dpr: 1.5, enableWebGL: true }
  }
}

export function useQualityTier(): QualityTierResult {
  const result = useMemo(() => computeQualityTier(), [])
  return result
}
