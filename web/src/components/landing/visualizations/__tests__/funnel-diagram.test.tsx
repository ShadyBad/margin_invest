import { render, screen } from "@testing-library/react"
import { describe, expect, test } from "vitest"
import { FunnelDiagram } from "../funnel-diagram"

describe("FunnelDiagram", () => {
  const defaultProps = {
    universeCount: 3056,
    eligibleCount: 842,
    scoredCount: 842,
    survivingCount: 12,
  }

  test("renders SVG with role img", () => {
    const { container } = render(<FunnelDiagram {...defaultProps} />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute("role", "img")
  })

  test("renders 4 funnel stages", () => {
    const { container } = render(<FunnelDiagram {...defaultProps} />)
    const stages = container.querySelectorAll("[data-funnel-stage]")
    expect(stages).toHaveLength(4)
  })

  test("displays formatted counts", () => {
    render(<FunnelDiagram {...defaultProps} />)
    expect(screen.getByText("3,056")).toBeInTheDocument()
    // 842 appears twice (eligible + scored are the same count)
    expect(screen.getAllByText("842")).toHaveLength(2)
    expect(screen.getByText("12")).toBeInTheDocument()
  })

  test("displays stage labels", () => {
    render(<FunnelDiagram {...defaultProps} />)
    expect(screen.getByText("Universe")).toBeInTheDocument()
    expect(screen.getByText("Eligible")).toBeInTheDocument()
    expect(screen.getByText("Scored")).toBeInTheDocument()
    expect(screen.getByText("Survivors")).toBeInTheDocument()
  })

  test("renders 3 connectors between stages", () => {
    const { container } = render(<FunnelDiagram {...defaultProps} />)
    const connectors = container.querySelectorAll("[data-funnel-connector]")
    expect(connectors).toHaveLength(3)
  })

  test("applies className", () => {
    const { container } = render(
      <FunnelDiagram {...defaultProps} className="my-funnel" />
    )
    const svg = container.querySelector("svg")
    expect(svg?.classList.contains("my-funnel")).toBe(true)
  })

  test("handles zero counts", () => {
    const { container } = render(
      <FunnelDiagram
        universeCount={0}
        eligibleCount={0}
        scoredCount={0}
        survivingCount={0}
      />
    )
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })
})
