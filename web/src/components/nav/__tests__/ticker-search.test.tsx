import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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

    it("positions overlay at top-[23px] to center in navbar", async () => {
      const user = userEvent.setup()
      render(<TickerSearch />)
      await user.click(screen.getByRole("button", { name: /search ticker/i }))
      const dialog = screen.getByRole("dialog")
      expect(dialog.className).toContain("top-[23px]")
    })
  })

  describe("submit behavior", () => {
    it("navigates to /asset/{TICKER} on submit", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "TSLA" } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).toHaveBeenCalledWith("/asset/TSLA")
    })

    it("uppercases the ticker before navigating", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "aapl" } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).toHaveBeenCalledWith("/asset/AAPL")
    })

    it("does not navigate on empty input", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "   " } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).not.toHaveBeenCalled()
    })

    it("closes the overlay after successful submit", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "MSFT" } })
      fireEvent.submit(input.closest("form")!)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
  })

  describe("keyboard shortcut", () => {
    it("opens overlay on Cmd+K", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k", metaKey: true })
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("opens overlay on Ctrl+K", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k", ctrlKey: true })
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("does not open on plain K key", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k" })
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
  })
})
