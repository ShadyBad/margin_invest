import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PriceContext } from "../price-context"

describe("PriceContext", () => {
  it("renders price context with all three rows", () => {
    render(
      <PriceContext actualPrice={150} buyPrice={120} marginOfSafety={-0.2} />
    )
    expect(screen.getByText(/current price/i)).toBeInTheDocument()
    expect(screen.getByText(/target price/i)).toBeInTheDocument()
    expect(screen.getByText(/margin of safety/i)).toBeInTheDocument()
  })

  it("formats current price correctly", () => {
    render(
      <PriceContext actualPrice={187.42} buyPrice={142} marginOfSafety={-0.24} />
    )
    expect(screen.getByText("$187.42")).toBeInTheDocument()
  })

  it("formats buy price correctly", () => {
    render(
      <PriceContext actualPrice={150} buyPrice={120} marginOfSafety={-0.2} />
    )
    expect(screen.getByText("$120.00")).toBeInTheDocument()
  })

  it("shows negative margin of safety in red", () => {
    render(
      <PriceContext actualPrice={150} buyPrice={120} marginOfSafety={-0.2} />
    )
    const marginValue = screen.getByTestId("margin-of-safety-value")
    expect(marginValue).toHaveTextContent("-20.0%")
    expect(marginValue.className).toContain("text-bearish")
  })

  it("shows positive margin of safety in green", () => {
    render(
      <PriceContext actualPrice={100} buyPrice={120} marginOfSafety={0.2} />
    )
    const marginValue = screen.getByTestId("margin-of-safety-value")
    expect(marginValue).toHaveTextContent("+20.0%")
    expect(marginValue.className).toContain("text-bullish")
  })

  it("shows zero margin of safety in green", () => {
    render(
      <PriceContext actualPrice={100} buyPrice={100} marginOfSafety={0} />
    )
    const marginValue = screen.getByTestId("margin-of-safety-value")
    expect(marginValue).toHaveTextContent("+0.0%")
    expect(marginValue.className).toContain("text-bullish")
  })

  it("has testid on root element", () => {
    render(
      <PriceContext actualPrice={150} buyPrice={120} marginOfSafety={-0.2} />
    )
    expect(screen.getByTestId("price-context")).toBeInTheDocument()
  })
})
