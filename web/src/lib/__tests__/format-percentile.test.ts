import { describe, it, expect } from "vitest"
import { formatPercentile } from "../format-percentile"

describe("formatPercentile", () => {
  it("rounds to nearest integer", () => {
    expect(formatPercentile(72)).toBe("72")
  })
  it("rounds float with many decimals", () => {
    expect(formatPercentile(99.574)).toBe("100")
  })
  it("handles zero", () => {
    expect(formatPercentile(0)).toBe("0")
  })
  it("clamps above 100", () => {
    expect(formatPercentile(105)).toBe("100")
  })
  it("clamps below 0", () => {
    expect(formatPercentile(-5)).toBe("0")
  })
})
