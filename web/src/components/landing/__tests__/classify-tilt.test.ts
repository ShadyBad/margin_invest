import { describe, it, expect } from "vitest"
import { classifyTilt } from "../classify-tilt"
import type { CandidateCard } from "../types"

function makeCandidate(
  overrides: Partial<CandidateCard> & { growth_percentile: number; value_percentile: number }
): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    composite_percentile: 75,
    conviction_level: "high",
    quality_percentile: 70,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("classifyTilt", () => {
  it("returns zero counts for empty array", () => {
    expect(classifyTilt([])).toEqual({ Value: 0, Blend: 0, Growth: 0 })
  })

  it("classifies growth-leaning candidate (diff > 10)", () => {
    const candidates = [makeCandidate({ growth_percentile: 80, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 0, Growth: 1 })
  })

  it("classifies value-leaning candidate (diff < -10)", () => {
    const candidates = [makeCandidate({ growth_percentile: 40, value_percentile: 70 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 1, Blend: 0, Growth: 0 })
  })

  it("classifies blend candidate (diff within threshold)", () => {
    const candidates = [makeCandidate({ growth_percentile: 55, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff exactly 10 is Blend", () => {
    const candidates = [makeCandidate({ growth_percentile: 60, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff exactly -10 is Blend", () => {
    const candidates = [makeCandidate({ growth_percentile: 50, value_percentile: 60 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff 11 is Growth", () => {
    const candidates = [makeCandidate({ growth_percentile: 61, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 0, Growth: 1 })
  })

  it("boundary: diff -11 is Value", () => {
    const candidates = [makeCandidate({ growth_percentile: 50, value_percentile: 61 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 1, Blend: 0, Growth: 0 })
  })

  it("counts multiple candidates across categories", () => {
    const candidates = [
      makeCandidate({ ticker: "A", growth_percentile: 80, value_percentile: 30 }), // Growth
      makeCandidate({ ticker: "B", growth_percentile: 20, value_percentile: 70 }), // Value
      makeCandidate({ ticker: "C", growth_percentile: 50, value_percentile: 55 }), // Blend
      makeCandidate({ ticker: "D", growth_percentile: 90, value_percentile: 40 }), // Growth
      makeCandidate({ ticker: "E", growth_percentile: 30, value_percentile: 80 }), // Value
    ]
    expect(classifyTilt(candidates)).toEqual({ Value: 2, Blend: 1, Growth: 2 })
  })
})
