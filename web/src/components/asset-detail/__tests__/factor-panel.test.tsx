import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FactorPanel } from "../factor-panel"

const factors = {
  quality: 85,
  value: 72,
  momentum: 65,
  sentiment: 58,
  growth: 90,
}

describe("FactorPanel", () => {
  it("renders factor panel with radar chart svg", () => {
    const { container } = render(<FactorPanel factors={factors} />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })

  it("has testid on root element", () => {
    render(<FactorPanel factors={factors} />)
    expect(screen.getByTestId("factor-panel")).toBeInTheDocument()
  })

  it("renders Factor Profile heading", () => {
    render(<FactorPanel factors={factors} />)
    expect(screen.getByText("Factor Profile")).toBeInTheDocument()
  })

  it("renders all five factor labels in the bars", () => {
    render(<FactorPanel factors={factors} />)
    expect(screen.getByText("QUALITY")).toBeInTheDocument()
    expect(screen.getByText("VALUE")).toBeInTheDocument()
    expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
    expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
    expect(screen.getByText("GROWTH")).toBeInTheDocument()
  })

  it("renders factor bar tracks", () => {
    const { container } = render(<FactorPanel factors={factors} />)
    const tracks = container.querySelectorAll("[data-factor-track]")
    expect(tracks.length).toBe(5)
  })

  it("renders factor numeric values", () => {
    render(<FactorPanel factors={factors} />)
    expect(screen.getByText("85")).toBeInTheDocument()
    expect(screen.getByText("72")).toBeInTheDocument()
    expect(screen.getByText("65")).toBeInTheDocument()
    expect(screen.getByText("58")).toBeInTheDocument()
    expect(screen.getByText("90")).toBeInTheDocument()
  })

  it("renders radar chart data polygon", () => {
    const { container } = render(<FactorPanel factors={factors} />)
    const dataPolygon = container.querySelector("[data-data-polygon]")
    expect(dataPolygon).toBeInTheDocument()
  })
})
