import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MobileMenu } from "../mobile-menu"
import type { NavigationState } from "@/hooks/use-navigation"

const publicNav: NavigationState = {
  isAuthenticated: false,
  links: [
    { href: "/methodology", label: "Methodology", isActive: false },
    { href: "/guides", label: "Guides", isActive: false },
  ],
  cta: {
    primary: { label: "Login", href: "/login" },
    secondary: { label: "Sign Up", href: "/register" },
  },
  user: null,
  logoHref: "/",
}

const appNav: NavigationState = {
  isAuthenticated: true,
  links: [
    { href: "/dashboard", label: "Dashboard", isActive: true },
    { href: "/", label: "Mainpage", isActive: false },
  ],
  cta: null,
  user: {
    name: "Jane Doe",
    email: "jane@example.com",
    avatarUrl: null,
    oauthAvatarUrl: null,
    dropdownItems: [
      { label: "Account", href: "/account", type: "link" },
      { label: "Settings", href: "/settings", type: "link" },
      { label: "", type: "divider" },
      { label: "Sign Out", onClick: vi.fn(), type: "action" },
    ],
  },
  logoHref: "/",
}

describe("MobileMenu", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <MobileMenu nav={publicNav} isOpen={false} onClose={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders links when open", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Guides")).toBeInTheDocument()
  })

  it("renders Login CTA for unauthenticated", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Login")).toBeInTheDocument()
  })

  it("renders user info for authenticated", () => {
    render(<MobileMenu nav={appNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
  })

  it("calls onClose when a link is clicked", async () => {
    const onClose = vi.fn()
    const u = userEvent.setup()
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={onClose} />)
    await u.click(screen.getByText("Methodology"))
    expect(onClose).toHaveBeenCalled()
  })
})
