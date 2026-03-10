import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { RadarChart } from "../radar-chart"

describe("RadarChart", () => {
  const factors = {
    quality: 85,
    value: 72,
    momentum: 65,
    sentiment: 58,
    growth: 90,
  }

  test("renders SVG with data polygon", () => {
    const { container } = render(<RadarChart factors={factors} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const polygons = container.querySelectorAll("polygon")
    expect(polygons.length).toBeGreaterThanOrEqual(2) // reference + data
  })

  test("renders 5 axis labels", () => {
    render(<RadarChart factors={factors} />)
    expect(screen.getByText(/quality/i)).toBeInTheDocument()
    expect(screen.getByText(/value/i)).toBeInTheDocument()
    expect(screen.getByText(/momentum/i)).toBeInTheDocument()
    expect(screen.getByText(/sentiment/i)).toBeInTheDocument()
    expect(screen.getByText(/growth/i)).toBeInTheDocument()
  })

  test("renders 5 axis lines from center", () => {
    const { container } = render(<RadarChart factors={factors} />)
    const axisLines = container.querySelectorAll("[data-axis-line]")
    expect(axisLines).toHaveLength(5)
  })

  test("renders 5 data points (circles)", () => {
    const { container } = render(<RadarChart factors={factors} />)
    const circles = container.querySelectorAll("[data-data-point]")
    expect(circles).toHaveLength(5)
  })

  test("applies className to container", () => {
    const { container } = render(
      <RadarChart factors={factors} className="my-radar" />
    )
    const svg = container.querySelector("svg")
    expect(svg?.classList.contains("my-radar")).toBe(true)
  })

  test("uses custom size", () => {
    const { container } = render(<RadarChart factors={factors} size={300} />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("viewBox", "0 0 300 300")
  })

  test("uses default size of 200", () => {
    const { container } = render(<RadarChart factors={factors} />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("viewBox", "0 0 200 200")
  })

  test("handles all-zero factors", () => {
    const zeroFactors = {
      quality: 0,
      value: 0,
      momentum: 0,
      sentiment: 0,
      growth: 0,
    }
    const { container } = render(<RadarChart factors={zeroFactors} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    // Should still have reference + data polygons
    const polygons = container.querySelectorAll("polygon")
    expect(polygons.length).toBeGreaterThanOrEqual(2)
  })

  test("handles max factors (all 100)", () => {
    const maxFactors = {
      quality: 100,
      value: 100,
      momentum: 100,
      sentiment: 100,
      growth: 100,
    }
    const { container } = render(<RadarChart factors={maxFactors} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const polygons = container.querySelectorAll("polygon")
    expect(polygons.length).toBeGreaterThanOrEqual(2)
  })
})
