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
})
