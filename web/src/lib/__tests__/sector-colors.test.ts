import { describe, it, expect } from "vitest"
import { getSectorColor, SECTOR_BORDER_COLOR } from "../sector-colors"

describe("SECTOR_BORDER_COLOR", () => {
  it("maps all 11 GICS sectors", () => {
    expect(Object.keys(SECTOR_BORDER_COLOR)).toHaveLength(11)
  })

  it("returns CSS variable references", () => {
    expect(SECTOR_BORDER_COLOR["Information Technology"]).toBe("var(--color-sector-tech)")
    expect(SECTOR_BORDER_COLOR["Energy"]).toBe("var(--color-sector-energy)")
  })
})

describe("getSectorColor", () => {
  it("returns sector color for known sector", () => {
    expect(getSectorColor("Information Technology")).toBe("var(--color-sector-tech)")
  })

  it("returns fallback for unknown sector", () => {
    expect(getSectorColor("Unknown")).toBe("var(--color-border-primary)")
  })

  it("returns fallback for null", () => {
    expect(getSectorColor(null)).toBe("var(--color-border-primary)")
  })

  it("returns fallback for undefined", () => {
    expect(getSectorColor(undefined)).toBe("var(--color-border-primary)")
  })
})
