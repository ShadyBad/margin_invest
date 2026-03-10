import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { FactorBars } from "../factor-bars"

describe("FactorBars", () => {
  const factors = { quality: 85, value: 72, momentum: 65, sentiment: 58, growth: 90 }

  test("renders all 5 factor labels", () => {
    render(<FactorBars factors={factors} />)
    expect(screen.getByText("QUALITY")).toBeInTheDocument()
    expect(screen.getByText("VALUE")).toBeInTheDocument()
    expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
    expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
    expect(screen.getByText("GROWTH")).toBeInTheDocument()
  })

  test("renders numeric percentile values", () => {
    render(<FactorBars factors={factors} />)
    expect(screen.getByText("85")).toBeInTheDocument()
    expect(screen.getByText("72")).toBeInTheDocument()
    expect(screen.getByText("65")).toBeInTheDocument()
    expect(screen.getByText("58")).toBeInTheDocument()
    expect(screen.getByText("90")).toBeInTheDocument()
  })

  test("renders bar elements with correct widths", () => {
    const { container } = render(<FactorBars factors={factors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    expect(bars).toHaveLength(5)
  })

  test("bar widths reflect percentile values", () => {
    const { container } = render(<FactorBars factors={factors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    expect(bars[0]).toHaveStyle({ width: "85%" })
    expect(bars[1]).toHaveStyle({ width: "72%" })
    expect(bars[2]).toHaveStyle({ width: "65%" })
    expect(bars[3]).toHaveStyle({ width: "58%" })
    expect(bars[4]).toHaveStyle({ width: "90%" })
  })

  test("applies correct color tiers based on percentile", () => {
    const tieredFactors = {
      quality: 10, // bearish (0-20)
      value: 30, // warning (20-40)
      momentum: 50, // neutral (40-60)
      sentiment: 70, // bullish (60-80)
      growth: 90, // exceptional (80-100)
    }
    const { container } = render(<FactorBars factors={tieredFactors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    // Verify each bar has a background color set via style
    expect(bars[0]).toHaveStyle({ backgroundColor: "#DC2626" }) // bearish/weak
    expect(bars[1]).toHaveStyle({ backgroundColor: "#D97706" }) // warning/below
    expect(bars[2]).toHaveStyle({ backgroundColor: "#6B7280" }) // neutral/average
    expect(bars[3]).toHaveStyle({ backgroundColor: "#1C7A5A" }) // bullish/strong
    expect(bars[4]).toHaveStyle({ backgroundColor: "#10B981" }) // exceptional
  })

  test("renders compact variant with smaller bars", () => {
    const { container } = render(<FactorBars factors={factors} compact />)
    const barTracks = container.querySelectorAll("[data-factor-track]")
    barTracks.forEach((track) => {
      expect(track.classList.contains("h-1")).toBe(true)
    })
  })

  test("renders normal variant with standard bar height", () => {
    const { container } = render(<FactorBars factors={factors} />)
    const barTracks = container.querySelectorAll("[data-factor-track]")
    barTracks.forEach((track) => {
      expect(track.classList.contains("h-1.5")).toBe(true)
    })
  })

  test("clamps values to 0-100 range", () => {
    const edgeFactors = {
      quality: -10,
      value: 150,
      momentum: 0,
      sentiment: 100,
      growth: 50,
    }
    const { container } = render(<FactorBars factors={edgeFactors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    expect(bars[0]).toHaveStyle({ width: "0%" })
    expect(bars[1]).toHaveStyle({ width: "100%" })
    expect(bars[2]).toHaveStyle({ width: "0%" })
    expect(bars[3]).toHaveStyle({ width: "100%" })
    expect(bars[4]).toHaveStyle({ width: "50%" })
  })
})
