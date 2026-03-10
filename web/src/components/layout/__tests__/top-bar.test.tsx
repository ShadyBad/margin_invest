import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TopBar } from "../top-bar"

describe("TopBar", () => {
  it("renders search input", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
  })

  it("renders menu toggle button", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    const button = screen.getByRole("button", { name: /toggle menu/i })
    expect(button).toBeInTheDocument()
  })

  it("calls onMenuToggle when hamburger is clicked", () => {
    const onMenuToggle = vi.fn()
    render(<TopBar onMenuToggle={onMenuToggle} />)
    fireEvent.click(screen.getByRole("button", { name: /toggle menu/i }))
    expect(onMenuToggle).toHaveBeenCalledTimes(1)
  })

  it("renders wordmark", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByText("margin")).toBeInTheDocument()
  })

  it("renders keyboard shortcut badge", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByText("K")).toBeInTheDocument()
  })

  it("renders help button", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByRole("button", { name: "Help" })).toBeInTheDocument()
  })

  it("renders settings button", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument()
  })

  it("renders user avatar", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByLabelText("User avatar")).toBeInTheDocument()
  })

  it("renders as a header element", () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByRole("banner")).toBeInTheDocument()
  })
})
