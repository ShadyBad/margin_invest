import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TopBar } from "../top-bar"

function renderTopBar(overrides: { sidebarExpanded?: boolean; onMenuToggle?: () => void } = {}) {
  const { sidebarExpanded = true, onMenuToggle = vi.fn() } = overrides
  return render(<TopBar sidebarExpanded={sidebarExpanded} onMenuToggle={onMenuToggle} />)
}

describe("TopBar", () => {
  it("renders search input", () => {
    renderTopBar()
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
  })

  it("renders menu toggle button", () => {
    renderTopBar()
    const button = screen.getByRole("button", { name: /toggle menu/i })
    expect(button).toBeInTheDocument()
  })

  it("calls onMenuToggle when hamburger is clicked", () => {
    const onMenuToggle = vi.fn()
    renderTopBar({ onMenuToggle })
    fireEvent.click(screen.getByRole("button", { name: /toggle menu/i }))
    expect(onMenuToggle).toHaveBeenCalledTimes(1)
  })

  it("renders logo link", () => {
    renderTopBar({ sidebarExpanded: true })
    expect(screen.getByLabelText("Margin Invest home")).toBeInTheDocument()
  })

  it("renders wordmark when sidebar is expanded", () => {
    renderTopBar({ sidebarExpanded: true })
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })

  it("hides logo link and wordmark when sidebar is collapsed", () => {
    renderTopBar({ sidebarExpanded: false })
    expect(screen.queryByLabelText("Margin Invest home")).not.toBeInTheDocument()
    expect(screen.queryByText("Margin Invest")).not.toBeInTheDocument()
  })

  it("renders keyboard shortcut badge", () => {
    renderTopBar()
    expect(screen.getByText("K")).toBeInTheDocument()
  })

  it("renders help button", () => {
    renderTopBar()
    expect(screen.getByLabelText("Help")).toBeInTheDocument()
    expect(screen.getByLabelText("Help").closest("a")).toHaveAttribute("href", "/support")
  })

  it("renders settings button", () => {
    renderTopBar()
    expect(screen.getByLabelText("Settings")).toBeInTheDocument()
    expect(screen.getByLabelText("Settings").closest("a")).toHaveAttribute("href", "/settings")
  })

  it("renders user avatar", () => {
    renderTopBar()
    expect(screen.getByLabelText("Account")).toBeInTheDocument()
    expect(screen.getByLabelText("Account").closest("a")).toHaveAttribute("href", "/account")
  })

  it("renders as a header element", () => {
    renderTopBar()
    expect(screen.getByRole("banner")).toBeInTheDocument()
  })
})
