import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

const mockPathname = vi.fn()
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}))

import { ConditionalFooter } from "../conditional-footer"

describe("ConditionalFooter", () => {
  it("renders footer on non-home pages", () => {
    mockPathname.mockReturnValue("/dashboard")
    render(<ConditionalFooter />)
    expect(screen.getByRole("contentinfo")).toBeInTheDocument()
  })

  it("hides footer on homepage", () => {
    mockPathname.mockReturnValue("/")
    const { container } = render(<ConditionalFooter />)
    expect(container.innerHTML).toBe("")
  })
})
