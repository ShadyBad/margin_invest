import { describe, it, expect } from "vitest"
import {
  computeSharpeRatio,
  computeMaxDrawdown,
  computeVolatility,
  computeInstitutionalMetrics,
} from "../compute-institutional-metrics"
import type { PriceBar, ScoreResponse } from "@/lib/api/types"

function makeBars(closes: number[]): PriceBar[] {
  return closes.map((close, i) => ({
    date: `2026-01-${String(i + 1).padStart(2, "0")}`,
    open: close,
    high: close * 1.01,
    low: close * 0.99,
    close,
    volume: 1000000,
    adj_close: close,
  }))
}

describe("computeSharpeRatio", () => {
  it("returns positive Sharpe for upward trending prices", () => {
    const closes = [100, 101, 102.01, 103.03, 104.06, 105.1, 106.15, 107.21, 108.28, 109.37]
    const result = computeSharpeRatio(makeBars(closes))
    expect(result).toBeGreaterThan(0)
  })

  it("returns null for insufficient data", () => {
    expect(computeSharpeRatio(makeBars([100, 101]))).toBeNull()
  })
})

describe("computeMaxDrawdown", () => {
  it("computes drawdown correctly for peak-to-trough", () => {
    // Peak at 200, trough at 150 = -25%
    const closes = [100, 150, 200, 180, 150, 160]
    const result = computeMaxDrawdown(makeBars(closes))
    expect(result).toBeCloseTo(-0.25, 2)
  })

  it("returns 0 for monotonically increasing prices", () => {
    const closes = [100, 110, 120, 130, 140]
    expect(computeMaxDrawdown(makeBars(closes))).toBe(0)
  })
})

describe("computeVolatility", () => {
  it("returns annualized volatility as a percentage", () => {
    const closes = [100, 102, 98, 103, 97, 105, 99, 104, 96, 101]
    const result = computeVolatility(makeBars(closes))
    expect(result).toBeGreaterThan(0)
    expect(result).toBeLessThan(200)
  })

  it("returns null for insufficient data", () => {
    expect(computeVolatility(makeBars([100]))).toBeNull()
  })
})

describe("computeInstitutionalMetrics", () => {
  it("returns all metrics from a score with price history", () => {
    const closes = Array.from({ length: 60 }, (_, i) => 100 + i * 0.5 + Math.sin(i) * 2)
    const score = {
      price_history: makeBars(closes),
      max_position_pct: 4.2,
      growth_stage: "mature",
    } as unknown as ScoreResponse

    const result = computeInstitutionalMetrics(score)
    expect(result).not.toBeNull()
    expect(result!.sharpeRatio).toBeDefined()
    expect(result!.maxDrawdown).toBeDefined()
    expect(result!.volatility).toBeDefined()
    expect(result!.riskClassification).toBe("Moderate")
    expect(result!.allocationWeight).toBe(4.2)
  })

  it("returns null when no price history", () => {
    const score = { price_history: null } as unknown as ScoreResponse
    expect(computeInstitutionalMetrics(score)).toBeNull()
  })
})
