import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { CorrelationGrid } from "../correlation-grid"

const TICKERS = ["AAPL", "MSFT", "JNJ"]
const MATRIX: (number | null)[][] = [
  [1.0, 0.82, 0.15],
  [0.82, 1.0, null],
  [0.15, null, 1.0],
]
const SAMPLE_SIZES = [
  [252, 250, 248],
  [250, 252, 10],
  [248, 10, 252],
]

describe("CorrelationGrid", () => {
  it("renders all ticker labels", () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    for (const ticker of TICKERS) {
      const elements = screen.getAllByText(ticker)
      expect(elements.length).toBe(2) // col header + row header
    }
  })

  it("renders numeric values for non-null cells", () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    expect(screen.getAllByText("0.82").length).toBe(2) // symmetric pair
    expect(screen.getAllByText("0.15").length).toBe(2)
  })

  it("renders dash for null cells", () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    const dashes = screen.getAllByText("\u2014")
    expect(dashes.length).toBe(2) // two null cells
  })

  it("renders diagonal as 1.00", () => {
    render(<CorrelationGrid tickers={TICKERS} matrix={MATRIX} />)
    const ones = screen.getAllByText("1.00")
    expect(ones.length).toBe(3)
  })

  it("shows tooltip on hover when enabled", async () => {
    const user = userEvent.setup()
    render(
      <CorrelationGrid
        tickers={TICKERS}
        matrix={MATRIX}
        sampleSizes={SAMPLE_SIZES}
        showTooltip
      />
    )
    const cells = screen.getAllByText("0.82")
    await user.hover(cells[0])
    // The tooltip renders rho = value and N = sample_size days
    expect(screen.getByText(/\u03C1 =/)).toBeInTheDocument()
    expect(screen.getByText(/N = 250 days/)).toBeInTheDocument()
  })

  it("does not show tooltip when disabled", async () => {
    const user = userEvent.setup()
    render(
      <CorrelationGrid
        tickers={TICKERS}
        matrix={MATRIX}
        sampleSizes={SAMPLE_SIZES}
        showTooltip={false}
      />
    )
    const cells = screen.getAllByText("0.82")
    await user.hover(cells[0])
    expect(screen.queryByText(/N =/)).toBeNull()
  })
})
