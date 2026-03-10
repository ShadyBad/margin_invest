import { render } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { Sparkline } from "../sparkline"

describe("Sparkline", () => {
  test("renders SVG with polyline", () => {
    const { container } = render(
      <Sparkline data={[50, 60, 55, 70, 65, 80]} />
    )
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const polyline = container.querySelector("polyline")
    expect(polyline).toBeInTheDocument()
  })

  test("handles empty data gracefully", () => {
    const { container } = render(<Sparkline data={[]} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    // No polyline when there's no data
    const polyline = container.querySelector("polyline")
    expect(polyline).toBeNull()
  })

  test("sets viewBox based on width and height props", () => {
    const { container } = render(
      <Sparkline data={[10, 20, 30]} width={200} height={80} />
    )
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("viewBox", "0 0 200 80")
  })

  test("uses default dimensions when none provided", () => {
    const { container } = render(<Sparkline data={[10, 20]} />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("viewBox", "0 0 120 48")
  })

  test("applies className to SVG", () => {
    const { container } = render(
      <Sparkline data={[10, 20]} className="my-sparkline" />
    )
    const svg = container.querySelector("svg")
    expect(svg?.classList.contains("my-sparkline")).toBe(true)
  })

  test("renders gradient fill below line", () => {
    const { container } = render(<Sparkline data={[10, 20, 30]} />)
    const linearGradient = container.querySelector("linearGradient")
    expect(linearGradient).toBeInTheDocument()
    // Should have a filled polygon/path for the gradient area
    const polygon = container.querySelector("polygon")
    expect(polygon).toBeInTheDocument()
  })

  test("handles single data point", () => {
    const { container } = render(<Sparkline data={[50]} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    // Single point should render a polyline with one point
    const polyline = container.querySelector("polyline")
    expect(polyline).toBeInTheDocument()
  })

  test("handles flat data (all same values)", () => {
    const { container } = render(<Sparkline data={[50, 50, 50, 50]} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const polyline = container.querySelector("polyline")
    expect(polyline).toBeInTheDocument()
  })
})
