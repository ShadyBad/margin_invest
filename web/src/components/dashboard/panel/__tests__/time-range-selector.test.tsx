import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TimeRangeSelector } from "../time-range-selector"

describe("TimeRangeSelector", () => {
  it("renders all range options", () => {
    render(<TimeRangeSelector value="3M" onChange={vi.fn()} />)
    expect(screen.getByText("1M")).toBeInTheDocument()
    expect(screen.getByText("3M")).toBeInTheDocument()
    expect(screen.getByText("6M")).toBeInTheDocument()
    expect(screen.getByText("1Y")).toBeInTheDocument()
    expect(screen.getByText("ALL")).toBeInTheDocument()
  })

  it("highlights the active range", () => {
    render(<TimeRangeSelector value="6M" onChange={vi.fn()} />)
    const active = screen.getByText("6M")
    expect(active.className).toContain("bg-")
  })

  it("calls onChange with new range", () => {
    const onChange = vi.fn()
    render(<TimeRangeSelector value="3M" onChange={onChange} />)
    fireEvent.click(screen.getByText("1Y"))
    expect(onChange).toHaveBeenCalledWith("1Y")
  })

  it("does not propagate click to parent", () => {
    const parentClick = vi.fn()
    const onChange = vi.fn()
    render(
      <div onClick={parentClick}>
        <TimeRangeSelector value="3M" onChange={onChange} />
      </div>
    )
    fireEvent.click(screen.getByText("1Y"))
    expect(parentClick).not.toHaveBeenCalled()
  })
})
