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
      quality: 10, // <33 = danger
      value: 30, // <33 = danger
      momentum: 50, // 33-65 = warning
      sentiment: 70, // >=66 = bullish
      growth: 90, // >=66 = bullish
    }
    const { container } = render(<FactorBars factors={tieredFactors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    // 3-tier system: danger (<33), warning (33-65), bullish (>=66)
    // Colors use CSS custom properties, so verify the style attribute contains the right token
    expect((bars[0] as HTMLElement).style.backgroundColor).toBe("var(--color-danger)")
    expect((bars[1] as HTMLElement).style.backgroundColor).toBe("var(--color-danger)")
    expect((bars[2] as HTMLElement).style.backgroundColor).toBe("var(--color-warning)")
    expect((bars[3] as HTMLElement).style.backgroundColor).toBe("var(--color-bullish)")
    expect((bars[4] as HTMLElement).style.backgroundColor).toBe("var(--color-bullish)")
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

  test("renders N/A for null factor values instead of a bar", () => {
    const nullFactors = {
      quality: 85,
      value: 72,
      momentum: 65,
      sentiment: null,
      growth: null,
    }
    render(<FactorBars factors={nullFactors} />)
    // Should show N/A labels for null factors
    const naLabels = screen.getAllByText("N/A")
    expect(naLabels).toHaveLength(2)
    // Should not render bars for null factors (only 3 bars for quality/value/momentum)
  })

  test("renders bars only for non-null factors when some are null", () => {
    const mixedFactors = {
      quality: 85,
      value: 72,
      momentum: 65,
      sentiment: null,
      growth: null,
    }
    const { container } = render(<FactorBars factors={mixedFactors} />)
    const bars = container.querySelectorAll("[data-factor-bar]")
    expect(bars).toHaveLength(3) // only quality, value, momentum
  })
})
