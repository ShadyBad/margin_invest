import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MobileMenu } from "../mobile-menu"
import type { NavigationState } from "@/hooks/use-navigation"

vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: "dark",
    setTheme: vi.fn(),
  }),
}))

const publicNav: NavigationState = {
  isAuthenticated: false,
  links: [],
  cta: { primary: { label: "Dashboard", href: "/login" } },
  user: null,
  logoHref: "/",
}

const appNav: NavigationState = {
  isAuthenticated: true,
  links: [
    { href: "/dashboard", label: "Dashboard", isActive: false },
    { href: "/guides", label: "Guides", isActive: false },
  ],
  cta: null,
  user: {
    name: "Jane Doe",
    email: "jane@example.com",
    avatarUrl: null,
    oauthAvatarUrl: null,
    dropdownItems: [
      { label: "Account", href: "/account", type: "link" },
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

  it("renders Guides link for authenticated", () => {
    render(<MobileMenu nav={appNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Guides")).toBeInTheDocument()
  })

  it("renders Dashboard button for unauthenticated", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
  })

  it("renders Dashboard link AND user info for authenticated", () => {
    render(<MobileMenu nav={appNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
  })

  it("renders user info for authenticated", () => {
    render(<MobileMenu nav={appNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
  })

  it("calls onClose when a link is clicked", async () => {
    const onClose = vi.fn()
    const u = userEvent.setup()
    render(<MobileMenu nav={appNav} isOpen={true} onClose={onClose} />)
    await u.click(screen.getByText("Guides"))
    expect(onClose).toHaveBeenCalled()
  })

  it("renders theme toggle when menu is open", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByRole("button", { name: /switch to (light|dark) mode/i })).toBeInTheDocument()
  })
})
