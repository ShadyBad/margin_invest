import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppShell } from "../app-shell"

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}))

describe("AppShell", () => {
  it("renders children", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    expect(screen.getByTestId("child")).toBeInTheDocument()
  })

  it("includes floating navigation", () => {
    render(<AppShell><div>Content</div></AppShell>)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })

  it("renders children inside main element", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    const main = screen.getByRole("main")
    expect(main).toBeInTheDocument()
    expect(main).toContainElement(screen.getByTestId("child"))
  })
})
