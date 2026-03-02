import { describe, it, expect } from "vitest"
import { formatEliminationPct } from "../format-elimination-pct"

describe("formatEliminationPct", () => {
  it("returns '0' when total is 0", () => {
    expect(formatEliminationPct(0, 0)).toBe("0")
  })

  it("returns '0' when eliminated is 0", () => {
    expect(formatEliminationPct(0, 7300)).toBe("0")
  })

  it("formats normal percentages to 2 decimals, strips trailing zeros", () => {
    // 2000/7300 = 27.397...% → "27.4"
    expect(formatEliminationPct(2000, 7300)).toBe("27.4")
  })

  it("formats a clean percentage without unnecessary decimals", () => {
    // 7300/7300 = 100% → "100"
    expect(formatEliminationPct(7300, 7300)).toBe("100")
  })

  it("does NOT round to 100 when the true value is less than 100", () => {
    // 7299/7300 = 99.9863...% — 2 decimals would give 99.99, fine
    expect(formatEliminationPct(7299, 7300)).toBe("99.99")
  })

  it("expands to 4 decimals when 2 decimals would round to 100", () => {
    // 72999/73000 = 99.99863...% — 2 decimals rounds to 100.00 → expand
    expect(formatEliminationPct(72999, 73000)).toBe("99.9986")
  })

  it("handles the typical case from production (e.g. 99.72%)", () => {
    // 5580/5600 = 99.642...% → "99.64"
    expect(formatEliminationPct(5580, 5600)).toBe("99.64")
  })

  it("handles exact 50%", () => {
    expect(formatEliminationPct(500, 1000)).toBe("50")
  })
})
