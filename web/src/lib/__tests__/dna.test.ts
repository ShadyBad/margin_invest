import { describe, it, expect } from "vitest"
import {
  computeDNA,
  blendSectorColors,
  SECTOR_COLORS,
  type DNAInput,
  type DNAOutput,
} from "../dna"

describe("SECTOR_COLORS", () => {
  it("maps all 11 GICS sectors to hex colors", () => {
    expect(Object.keys(SECTOR_COLORS)).toHaveLength(11)
    expect(SECTOR_COLORS["Information Technology"]).toBe("#1A3A5C")
    expect(SECTOR_COLORS["Energy"]).toBe("#4A3018")
    expect(SECTOR_COLORS["Health Care"]).toBe("#0E4F4F")
  })
})

describe("blendSectorColors", () => {
  it("returns single sector color when portfolio is concentrated", () => {
    const result = blendSectorColors({ "Information Technology": 1.0 })
    expect(result.base).toBe("#1A3A5C")
  })

  it("blends two sectors by weight", () => {
    const result = blendSectorColors({
      "Information Technology": 0.5,
      "Energy": 0.5,
    })
    // Midpoint between #1A3A5C and #4A3018 = approximately #32353A
    expect(result.base).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.mid).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.accent).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it("returns default palette for empty input", () => {
    const result = blendSectorColors({})
    expect(result.base).toBe("#0F0D0B")
    expect(result.mid).toBe("#1A5A3E")
    expect(result.accent).toBe("#1A7A5A")
  })
})

describe("computeDNA", () => {
  it("computes full DNA output from portfolio data", () => {
    const input: DNAInput = {
      sectorWeights: { "Information Technology": 0.6, "Health Care": 0.4 },
      tickerCount: 8,
      avgBeta: 1.1,
    }
    const result: DNAOutput = computeDNA(input)
    expect(result.base).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.mid).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.accent).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.density).toBeGreaterThanOrEqual(0)
    expect(result.density).toBeLessThanOrEqual(1)
    expect(result.tempo).toBeGreaterThanOrEqual(0.5)
    expect(result.tempo).toBeLessThanOrEqual(1.5)
  })

  it("maps low ticker count to low density", () => {
    const result = computeDNA({
      sectorWeights: { "Energy": 1.0 },
      tickerCount: 2,
      avgBeta: 1.0,
    })
    expect(result.density).toBeLessThan(0.3)
  })

  it("maps high beta to faster tempo", () => {
    const result = computeDNA({
      sectorWeights: { "Information Technology": 1.0 },
      tickerCount: 10,
      avgBeta: 1.8,
    })
    expect(result.tempo).toBeGreaterThan(1.0)
  })

  it("maps low beta to slower tempo", () => {
    const result = computeDNA({
      sectorWeights: { "Utilities": 1.0 },
      tickerCount: 10,
      avgBeta: 0.5,
    })
    expect(result.tempo).toBeLessThan(1.0)
  })

  it("returns defaults for empty portfolio", () => {
    const result = computeDNA({
      sectorWeights: {},
      tickerCount: 0,
      avgBeta: 1.0,
    })
    expect(result.base).toBe("#0F0D0B")
    expect(result.density).toBe(0)
    expect(result.tempo).toBe(1.0)
  })
})
