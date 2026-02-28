import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import { AnalysisDisclaimerModal } from "../analysis-disclaimer-modal"

describe("AnalysisDisclaimerModal", () => {
  let store: Record<string, string> = {}
  const mockGetItem = vi.fn((key: string) => store[key] ?? null)
  const mockSetItem = vi.fn((key: string, value: string) => { store[key] = value })
  const mockRemoveItem = vi.fn((key: string) => { delete store[key] })

  beforeEach(() => {
    store = {}
    mockGetItem.mockClear()
    mockSetItem.mockClear()
    mockRemoveItem.mockClear()

    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: mockGetItem,
        setItem: mockSetItem,
        removeItem: mockRemoveItem,
        clear: () => { store = {} },
        length: 0,
        key: () => null,
      },
      writable: true,
      configurable: true,
    })
  })

  it("is not visible initially", () => {
    render(<AnalysisDisclaimerModal />)
    expect(screen.queryByTestId("analysis-disclaimer-modal")).not.toBeInTheDocument()
  })

  it("appears when analysis-disclaimer-required event is dispatched", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(screen.getByTestId("analysis-disclaimer-modal")).toBeInTheDocument()
  })

  it("displays correct title", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(
      screen.getByRole("heading", { name: "Quantitative Analysis Tool" })
    ).toBeInTheDocument()
  })

  it("displays disclaimer text", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(
      screen.getByText(/does not provide investment advice/)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/not predictions of future performance/)
    ).toBeInTheDocument()
  })

  it("'I Understand' button sets localStorage and closes modal", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(screen.getByTestId("analysis-disclaimer-modal")).toBeInTheDocument()

    fireEvent.click(screen.getByTestId("disclaimer-accept"))

    expect(screen.queryByTestId("analysis-disclaimer-modal")).not.toBeInTheDocument()
    expect(mockSetItem).toHaveBeenCalledWith("disclaimer_acknowledged", "true")
  })

  it("does not open if already acknowledged", () => {
    store["disclaimer_acknowledged"] = "true"

    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(screen.queryByTestId("analysis-disclaimer-modal")).not.toBeInTheDocument()
  })

  it("has proper dialog role and aria attributes", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(dialog).toHaveAttribute("aria-labelledby", "analysis-disclaimer-title")
  })

  it("backdrop does not dismiss the modal", () => {
    render(<AnalysisDisclaimerModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("analysis-disclaimer-required"))
    })

    expect(screen.getByTestId("analysis-disclaimer-modal")).toBeInTheDocument()

    // Click the backdrop
    const backdrop = screen.getByTestId("analysis-disclaimer-modal").querySelector("[aria-hidden='true']")
    expect(backdrop).toBeTruthy()
    fireEvent.click(backdrop!)

    // Modal should still be open — no dismiss on backdrop click
    expect(screen.getByTestId("analysis-disclaimer-modal")).toBeInTheDocument()
  })
})
