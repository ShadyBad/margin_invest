import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TickerSearch } from "../ticker-search"

// Mock next/navigation
const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe("TickerSearch", () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  it("renders search input", () => {
    render(<TickerSearch />)
    expect(screen.getByPlaceholderText(/Search any ticker/i)).toBeInTheDocument()
  })

  it("navigates to /asset/{TICKER} on submit", () => {
    render(<TickerSearch />)
    const input = screen.getByPlaceholderText(/Search any ticker/i)
    fireEvent.change(input, { target: { value: "TSLA" } })
    fireEvent.submit(input.closest("form")!)
    expect(pushMock).toHaveBeenCalledWith("/asset/TSLA")
  })

  it("uppercases the ticker before navigating", () => {
    render(<TickerSearch />)
    const input = screen.getByPlaceholderText(/Search any ticker/i)
    fireEvent.change(input, { target: { value: "aapl" } })
    fireEvent.submit(input.closest("form")!)
    expect(pushMock).toHaveBeenCalledWith("/asset/AAPL")
  })

  it("does not navigate on empty input", () => {
    render(<TickerSearch />)
    const input = screen.getByPlaceholderText(/Search any ticker/i)
    fireEvent.change(input, { target: { value: "   " } })
    fireEvent.submit(input.closest("form")!)
    expect(pushMock).not.toHaveBeenCalled()
  })

  it("clears input after successful submit", () => {
    render(<TickerSearch />)
    const input = screen.getByPlaceholderText(/Search any ticker/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: "MSFT" } })
    fireEvent.submit(input.closest("form")!)
    expect(input.value).toBe("")
  })
})
