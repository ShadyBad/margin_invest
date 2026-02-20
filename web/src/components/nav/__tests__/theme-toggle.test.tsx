import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThemeToggle } from "../theme-toggle"

// Mock next-themes
const mockSetTheme = vi.fn()
let mockResolvedTheme = "dark"

vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: mockResolvedTheme,
    setTheme: mockSetTheme,
  }),
}))

describe("ThemeToggle", () => {
  beforeEach(() => {
    mockSetTheme.mockClear()
    mockResolvedTheme = "dark"
  })

  it("renders a button with accessible label", () => {
    render(<ThemeToggle />)
    expect(screen.getByRole("button", { name: /switch to light mode/i })).toBeInTheDocument()
  })

  it("shows sun icon in dark mode (meaning: switch to light)", () => {
    mockResolvedTheme = "dark"
    render(<ThemeToggle />)
    const button = screen.getByRole("button", { name: /switch to light mode/i })
    expect(button.querySelector("svg")).toBeInTheDocument()
  })

  it("shows moon icon in light mode (meaning: switch to dark)", () => {
    mockResolvedTheme = "light"
    render(<ThemeToggle />)
    const button = screen.getByRole("button", { name: /switch to dark mode/i })
    expect(button.querySelector("svg")).toBeInTheDocument()
  })

  it("calls setTheme('light') when clicked in dark mode", async () => {
    mockResolvedTheme = "dark"
    const u = userEvent.setup()
    render(<ThemeToggle />)
    await u.click(screen.getByRole("button", { name: /switch to light mode/i }))
    expect(mockSetTheme).toHaveBeenCalledWith("light")
  })

  it("calls setTheme('dark') when clicked in light mode", async () => {
    mockResolvedTheme = "light"
    const u = userEvent.setup()
    render(<ThemeToggle />)
    await u.click(screen.getByRole("button", { name: /switch to dark mode/i }))
    expect(mockSetTheme).toHaveBeenCalledWith("dark")
  })

  it("has correct aria-label for dark mode", () => {
    mockResolvedTheme = "dark"
    render(<ThemeToggle />)
    expect(screen.getByRole("button")).toHaveAttribute("aria-label", "Switch to light mode")
  })

  it("has correct aria-label for light mode", () => {
    mockResolvedTheme = "light"
    render(<ThemeToggle />)
    expect(screen.getByRole("button")).toHaveAttribute("aria-label", "Switch to dark mode")
  })
})
