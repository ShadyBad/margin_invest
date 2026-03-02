import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TickerSearch } from "../ticker-search"

const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe("TickerSearch", () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  describe("icon button (default state)", () => {
    it("renders a search button with magnifying glass icon", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      expect(button).toBeInTheDocument()
      expect(button.querySelector("svg")).toBeInTheDocument()
    })

    it("does not show the search overlay by default", () => {
      render(<TickerSearch />)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("has correct ARIA attributes", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      expect(button).toHaveAttribute("aria-haspopup", "dialog")
      expect(button).toHaveAttribute("aria-expanded", "false")
    })
  })

  describe("overlay (open state)", () => {
    it("opens the search overlay when icon is clicked", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("sets aria-expanded to true when open", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      fireEvent.click(button)
      expect(button).toHaveAttribute("aria-expanded", "true")
    })

    it("auto-focuses the input when overlay opens", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      expect(input).toHaveFocus()
    })

    it("closes the overlay on Escape key", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      expect(screen.getByRole("dialog")).toBeInTheDocument()
      fireEvent.keyDown(screen.getByLabelText(/ticker symbol/i), { key: "Escape" })
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("closes the overlay on backdrop click", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const backdrop = screen.getByTestId("search-backdrop")
      fireEvent.click(backdrop)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("has correct ARIA attributes on the dialog", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const dialog = screen.getByRole("dialog")
      expect(dialog).toHaveAttribute("aria-label", "Ticker search")
      expect(dialog).toHaveAttribute("aria-modal", "true")
    })
  })
})
