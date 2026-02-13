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
})
