import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppShell } from "../app-shell"

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

describe("AppShell", () => {
  it("renders children", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    expect(screen.getByTestId("child")).toBeInTheDocument()
  })

  it("includes sidebar navigation", () => {
    render(<AppShell><div>Content</div></AppShell>)
    const nav = screen.getByRole("navigation", { name: "Sidebar navigation" })
    expect(nav).toBeInTheDocument()
  })

  it("renders children inside main element", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    const main = screen.getByRole("main")
    expect(main).toBeInTheDocument()
    expect(main).toContainElement(screen.getByTestId("child"))
  })

  it("renders the top bar", () => {
    render(<AppShell><div>Content</div></AppShell>)
    expect(screen.getByRole("banner")).toBeInTheDocument()
  })

  it("renders the sidebar", () => {
    render(<AppShell><div>Content</div></AppShell>)
    expect(screen.getByTestId("sidebar")).toBeInTheDocument()
  })

  it("renders menu toggle button", () => {
    render(<AppShell><div>Content</div></AppShell>)
    expect(screen.getByRole("button", { name: /toggle menu/i })).toBeInTheDocument()
  })
})
