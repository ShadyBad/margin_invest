import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { AccountPillNav } from "../account-pill-nav"

const sections = ["Profile", "Security", "Billing"]

describe("AccountPillNav", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders all section pills as buttons", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    for (const section of sections) {
      expect(screen.getByRole("button", { name: section })).toBeInTheDocument()
    }
  })

  it("highlights the active section with text-accent", () => {
    render(<AccountPillNav sections={sections} activeSection="Security" />)
    const activeButton = screen.getByRole("button", { name: "Security" })
    expect(activeButton.className).toContain("text-accent")
    expect(activeButton.className).toContain("bg-accent/10")
  })

  it("does not highlight inactive sections with text-accent", () => {
    render(<AccountPillNav sections={sections} activeSection="Security" />)
    const inactiveButton = screen.getByRole("button", { name: "Profile" })
    expect(inactiveButton.className).not.toContain("text-accent")
    expect(inactiveButton.className).toContain("text-text-secondary")
  })

  it("calls onNavigate when a pill is clicked", () => {
    const onNavigate = vi.fn()
    render(
      <AccountPillNav
        sections={sections}
        activeSection="Profile"
        onNavigate={onNavigate}
      />
    )
    fireEvent.click(screen.getByRole("button", { name: "Billing" }))
    expect(onNavigate).toHaveBeenCalledWith("Billing")
    expect(onNavigate).toHaveBeenCalledTimes(1)
  })

  it("renders with nav role and correct aria-label", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    const nav = screen.getByRole("navigation", { name: "Account sections" })
    expect(nav).toBeInTheDocument()
  })

  it("applies rounded-lg to all pills", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    for (const section of sections) {
      const button = screen.getByRole("button", { name: section })
      expect(button.className).toContain("rounded-lg")
    }
  })

  it("does not crash when onNavigate is not provided", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    expect(() => {
      fireEvent.click(screen.getByRole("button", { name: "Billing" }))
    }).not.toThrow()
  })
})
