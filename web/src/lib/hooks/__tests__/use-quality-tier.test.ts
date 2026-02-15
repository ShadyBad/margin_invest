import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { useQualityTier } from "../use-quality-tier"

describe("useQualityTier", () => {
  beforeEach(() => {
    vi.stubGlobal("innerWidth", 1440)
    vi.stubGlobal("navigator", { hardwareConcurrency: 8 })
  })

  it("returns 'high' for desktop with good GPU", () => {
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("high")
    expect(result.current.dpr).toBe(1.5)
    expect(result.current.enableWebGL).toBe(true)
  })

  it("returns 'medium' for tablet viewport", () => {
    vi.stubGlobal("innerWidth", 900)
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("medium")
    expect(result.current.dpr).toBe(1)
    expect(result.current.enableWebGL).toBe(true)
  })

  it("returns 'low' for mobile viewport", () => {
    vi.stubGlobal("innerWidth", 375)
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("low")
    expect(result.current.enableWebGL).toBe(false)
  })

  it("returns 'medium' for desktop with weak CPU", () => {
    vi.stubGlobal("navigator", { hardwareConcurrency: 2 })
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("medium")
  })
})
