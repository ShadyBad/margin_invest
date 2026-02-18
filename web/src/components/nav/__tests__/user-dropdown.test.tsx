import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { UserDropdown } from "../user-dropdown"
import type { NavigationUser } from "@/hooks/use-navigation"

const mockSignOut = vi.fn()

const user: NavigationUser = {
  name: "Jane Doe",
  email: "jane@example.com",
  avatarUrl: null,
  oauthAvatarUrl: null,
  dropdownItems: [
    { label: "Account", href: "/account", type: "link" },
    { label: "", type: "divider" },
    { label: "Sign Out", onClick: mockSignOut, type: "action" },
  ],
}

describe("UserDropdown", () => {
  beforeEach(() => {
    mockSignOut.mockClear()
  })

  it("renders the avatar button", () => {
    render(<UserDropdown user={user} />)
    expect(screen.getByRole("button", { name: /user menu/i })).toBeInTheDocument()
  })

  it("dropdown is closed by default", () => {
    render(<UserDropdown user={user} />)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("opens dropdown on avatar click", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
  })

  it("renders dropdown items when open", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("Account")).toBeInTheDocument()
    expect(screen.getByText("Sign Out")).toBeInTheDocument()
  })

  it("renders link items as anchor tags", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("Account").closest("a")).toHaveAttribute("href", "/account")
  })

  it("calls onClick for action items", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    await u.click(screen.getByText("Sign Out"))
    expect(mockSignOut).toHaveBeenCalled()
  })

  it("renders divider separator", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("separator")).toBeInTheDocument()
  })

  it("closes on second click (toggle)", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    const trigger = screen.getByRole("button", { name: /user menu/i })
    await u.click(trigger)
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.click(trigger)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("closes on Escape key", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.keyboard("{Escape}")
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("closes dropdown when link item is clicked", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.click(screen.getByText("Account"))
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("has aria-expanded on trigger button", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    const trigger = screen.getByRole("button", { name: /user menu/i })
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    await u.click(trigger)
    expect(trigger).toHaveAttribute("aria-expanded", "true")
  })
})
