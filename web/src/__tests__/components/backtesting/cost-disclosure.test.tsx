import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { CostDisclosure } from "@/components/backtesting/cost-disclosure"

describe("CostDisclosure", () => {
  it("renders the component", () => {
    render(<CostDisclosure />)
    expect(screen.getByTestId("cost-disclosure")).toBeInTheDocument()
  })

  it("has a clickable toggle", () => {
    render(<CostDisclosure />)
    expect(screen.getByTestId("cost-disclosure-toggle")).toBeInTheDocument()
  })

  it("shows commission assumption when open", () => {
    render(<CostDisclosure />)
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/5 bps/)).toBeInTheDocument()
  })

  it("shows not modeled section", () => {
    render(<CostDisclosure />)
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/not modeled/i)).toBeInTheDocument()
  })

  it("shows academic validation when provided", () => {
    render(
      <CostDisclosure
        costValidation={{
          model_cost_bps: 12,
          benchmark_range_bps: [10, 20],
          status: "within_range",
          source: "Frazzini, Israel & Moskowitz (2015)",
        }}
      />
    )
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/Frazzini/)).toBeInTheDocument()
  })

  it("does not show academic validation when not provided", () => {
    render(<CostDisclosure />)
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.queryByText(/Frazzini/)).not.toBeInTheDocument()
  })

  it("shows within_range message with bullish color", () => {
    render(
      <CostDisclosure
        costValidation={{
          model_cost_bps: 12,
          benchmark_range_bps: [10, 20],
          status: "within_range",
          source: "Frazzini, Israel & Moskowitz (2015)",
        }}
      />
    )
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/within the 10-20 bps range/)).toBeInTheDocument()
  })

  it("shows below_benchmark message with warning color", () => {
    render(
      <CostDisclosure
        costValidation={{
          model_cost_bps: 8,
          benchmark_range_bps: [10, 20],
          status: "below_benchmark",
          source: "Frazzini, Israel & Moskowitz (2015)",
        }}
      />
    )
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/potentially optimistic/)).toBeInTheDocument()
  })

  it("shows above_benchmark message with warning color", () => {
    render(
      <CostDisclosure
        costValidation={{
          model_cost_bps: 25,
          benchmark_range_bps: [10, 20],
          status: "above_benchmark",
          source: "Frazzini, Israel & Moskowitz (2015)",
        }}
      />
    )
    const details = screen.getByTestId("cost-disclosure")
    details.setAttribute("open", "")
    expect(screen.getByText(/exceeds the 10-20 bps range.*conservative/)).toBeInTheDocument()
  })
})
