import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { KnobsPanel } from "../knobs-panel"

const defaultProps = {
  rebalanceFrequency: "monthly",
  topPercentile: 20,
  transactionCostBps: 10,
  slippageBps: 5,
  benchmarkTicker: "SPY",
}

describe("KnobsPanel", () => {
  it("renders all parameter labels", () => {
    render(<KnobsPanel {...defaultProps} />)

    expect(screen.getByText("PARAMETERS")).toBeInTheDocument()
    expect(screen.getByText("Rebalance Frequency")).toBeInTheDocument()
    expect(screen.getByText("Top Percentile")).toBeInTheDocument()
    expect(screen.getByText("Transaction Cost")).toBeInTheDocument()
    expect(screen.getByText("Slippage")).toBeInTheDocument()
    expect(screen.getByText("Benchmark")).toBeInTheDocument()
  })

  it("shows current values in inputs", () => {
    render(<KnobsPanel {...defaultProps} />)

    const frequencySelect = screen.getByTestId("knob-rebalance-frequency") as HTMLSelectElement
    expect(frequencySelect.value).toBe("monthly")

    const percentileInput = screen.getByTestId("knob-top-percentile") as HTMLInputElement
    expect(percentileInput.value).toBe("20")

    const costInput = screen.getByTestId("knob-transaction-cost") as HTMLInputElement
    expect(costInput.value).toBe("10")

    const slippageInput = screen.getByTestId("knob-slippage") as HTMLInputElement
    expect(slippageInput.value).toBe("5")

    expect(screen.getByText("SPY")).toBeInTheDocument()
  })

  it("calls onRebalanceChange when frequency is changed", () => {
    const onChange = vi.fn()
    render(<KnobsPanel {...defaultProps} onRebalanceChange={onChange} />)

    const select = screen.getByTestId("knob-rebalance-frequency")
    fireEvent.change(select, { target: { value: "quarterly" } })

    expect(onChange).toHaveBeenCalledWith("quarterly")
  })

  it("calls onTopPercentileChange when slider is changed", () => {
    const onChange = vi.fn()
    render(<KnobsPanel {...defaultProps} onTopPercentileChange={onChange} />)

    const slider = screen.getByTestId("knob-top-percentile")
    fireEvent.change(slider, { target: { value: "30" } })

    expect(onChange).toHaveBeenCalledWith(30)
  })

  it("calls onTransactionCostChange when cost is changed", () => {
    const onChange = vi.fn()
    render(<KnobsPanel {...defaultProps} onTransactionCostChange={onChange} />)

    const input = screen.getByTestId("knob-transaction-cost")
    fireEvent.change(input, { target: { value: "15" } })

    expect(onChange).toHaveBeenCalledWith(15)
  })

  it("calls onSlippageChange when slippage is changed", () => {
    const onChange = vi.fn()
    render(<KnobsPanel {...defaultProps} onSlippageChange={onChange} />)

    const input = screen.getByTestId("knob-slippage")
    fireEvent.change(input, { target: { value: "8" } })

    expect(onChange).toHaveBeenCalledWith(8)
  })

  it("disables inputs when disabled=true", () => {
    render(<KnobsPanel {...defaultProps} disabled />)

    const frequencySelect = screen.getByTestId("knob-rebalance-frequency") as HTMLSelectElement
    expect(frequencySelect.disabled).toBe(true)

    const percentileInput = screen.getByTestId("knob-top-percentile") as HTMLInputElement
    expect(percentileInput.disabled).toBe(true)

    const costInput = screen.getByTestId("knob-transaction-cost") as HTMLInputElement
    expect(costInput.disabled).toBe(true)

    const slippageInput = screen.getByTestId("knob-slippage") as HTMLInputElement
    expect(slippageInput.disabled).toBe(true)
  })

  it("shows percentile value display", () => {
    render(<KnobsPanel {...defaultProps} topPercentile={35} />)
    expect(screen.getByText("35%")).toBeInTheDocument()
  })
})
