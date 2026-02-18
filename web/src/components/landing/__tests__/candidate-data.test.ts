import { describe, it, expect } from "vitest"
import { FALLBACK_CANDIDATES } from "../candidate-data"

describe("FALLBACK_CANDIDATES", () => {
  it("contains 3-5 candidates", () => {
    expect(FALLBACK_CANDIDATES.length).toBeGreaterThanOrEqual(3)
    expect(FALLBACK_CANDIDATES.length).toBeLessThanOrEqual(5)
  })

  it("every candidate has required fields", () => {
    for (const c of FALLBACK_CANDIDATES) {
      expect(c.ticker).toBeTruthy()
      expect(c.name).toBeTruthy()
      expect(c.sector).toBeTruthy()
      expect(c.actual_price).toBeGreaterThan(0)
      expect(c.buy_price).toBeGreaterThan(0)
      expect(c.composite_percentile).toBeGreaterThanOrEqual(0)
      expect(c.composite_percentile).toBeLessThanOrEqual(100)
      expect(c.quality_percentile).toBeGreaterThanOrEqual(0)
      expect(c.value_percentile).toBeGreaterThanOrEqual(0)
      expect(c.momentum_percentile).toBeGreaterThanOrEqual(0)
    }
  })

  it("every candidate has margin_of_safety between 0 and 1", () => {
    for (const c of FALLBACK_CANDIDATES) {
      expect(c.margin_of_safety).toBeGreaterThan(0)
      expect(c.margin_of_safety).toBeLessThan(1)
    }
  })
})
