import { render, screen, fireEvent } from "@testing-library/react"
import { TickerInput } from "../ticker-input"

describe("TickerInput", () => {
  it("renders input field with placeholder", () => {
    render(<TickerInput onSubmit={vi.fn()} />)
    expect(screen.getByPlaceholderText("AAPL, MSFT, GOOGL")).toBeInTheDocument()
  })

  it("calls onSubmit with parsed tickers", () => {
    const onSubmit = vi.fn()
    render(<TickerInput onSubmit={onSubmit} />)
    const input = screen.getByPlaceholderText("AAPL, MSFT, GOOGL")
    fireEvent.change(input, { target: { value: "AAPL, MSFT, GOOGL" } })
    fireEvent.click(screen.getByText("Score my positions"))
    expect(onSubmit).toHaveBeenCalledWith(["AAPL", "MSFT", "GOOGL"])
  })

  it("disables submit with empty input", () => {
    render(<TickerInput onSubmit={vi.fn()} />)
    const button = screen.getByText("Score my positions")
    expect(button).toBeDisabled()
  })

  it("uppercases and trims tickers", () => {
    const onSubmit = vi.fn()
    render(<TickerInput onSubmit={onSubmit} />)
    const input = screen.getByPlaceholderText("AAPL, MSFT, GOOGL")
    fireEvent.change(input, { target: { value: " aapl , msft " } })
    fireEvent.click(screen.getByText("Score my positions"))
    expect(onSubmit).toHaveBeenCalledWith(["AAPL", "MSFT"])
  })
})
