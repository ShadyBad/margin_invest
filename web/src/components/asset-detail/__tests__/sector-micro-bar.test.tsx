import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectorMicroBar } from "../sector-micro-bar"

describe("SectorMicroBar", () => {
  it("renders the bar with stock position marker", () => {
    render(<SectorMicroBar percentile={87} />)
    expect(screen.getByTestId("sector-micro-bar")).toBeInTheDocument()
    const dot = screen.getByTestId("stock-position")
    expect(dot.style.left).toBe("87%")
  })

  it("shows median and p90 markers", () => {
    render(<SectorMicroBar percentile={50} />)
    expect(screen.getByTestId("median-marker")).toBeInTheDocument()
    expect(screen.getByTestId("p90-marker")).toBeInTheDocument()
  })

  it("applies exceptional color for high percentiles", () => {
    render(<SectorMicroBar percentile={95} />)
    const fill = screen.getByTestId("percentile-fill")
    expect(fill.className).toContain("bg-[var(--color-percentile-exceptional)]")
  })

  it("applies weak color for low percentiles", () => {
    render(<SectorMicroBar percentile={15} />)
    const fill = screen.getByTestId("percentile-fill")
    expect(fill.className).toContain("bg-[var(--color-percentile-weak)]")
  })
})
