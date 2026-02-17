import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PercentileBar } from "../percentile-bar"

describe("PercentileBar", () => {
  it("renders value", () => {
    render(<PercentileBar value={75} />)
    expect(screen.getByText("75")).toBeInTheDocument()
  })

  it("renders label when provided", () => {
    render(<PercentileBar value={50} label="Quality" />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })

  it("clamps value above 100", () => {
    render(<PercentileBar value={150} />)
    expect(screen.getByText("100")).toBeInTheDocument()
  })

  it("clamps value below 0", () => {
    render(<PercentileBar value={-10} />)
    expect(screen.getByText("0")).toBeInTheDocument()
  })

  it("hides value when showValue is false", () => {
    render(<PercentileBar value={75} showValue={false} />)
    expect(screen.queryByText("75")).not.toBeInTheDocument()
  })

  it("renders exceptional tier (90-100) with bright green", () => {
    const { container } = render(<PercentileBar value={95} label="Quality" />)
    const bar = container.querySelector("[style]")
    expect(bar?.className).toContain("bg-percentile-exceptional")
  })

  it("renders strong tier (70-89) with emerald", () => {
    const { container } = render(<PercentileBar value={75} label="Quality" />)
    const bar = container.querySelector("[style]")
    expect(bar?.className).toContain("bg-percentile-strong")
  })

  it("renders average tier (50-69) with gray", () => {
    const { container } = render(<PercentileBar value={55} label="Quality" />)
    const bar = container.querySelector("[style]")
    expect(bar?.className).toContain("bg-percentile-average")
  })

  it("renders below-average tier (30-49) with amber", () => {
    const { container } = render(<PercentileBar value={35} label="Quality" />)
    const bar = container.querySelector("[style]")
    expect(bar?.className).toContain("bg-percentile-below")
  })

  it("renders weak tier (0-29) with red", () => {
    const { container } = render(<PercentileBar value={15} label="Quality" />)
    const bar = container.querySelector("[style]")
    expect(bar?.className).toContain("bg-percentile-weak")
  })
})
