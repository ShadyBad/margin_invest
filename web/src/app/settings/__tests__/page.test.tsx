import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import SettingsPage from "../page"

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: {
      user: {
        name: "Test User",
        email: "test@example.com",
        image: "https://example.com/avatar.jpg",
      },
    },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
}))

describe("Settings Page", () => {
  it("renders the settings heading", () => {
    render(<SettingsPage />)
    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument()
  })

  it("renders account section with user info", () => {
    render(<SettingsPage />)
    expect(screen.getByRole("heading", { name: "Account" })).toBeInTheDocument()
    expect(screen.getAllByText("Test User").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("test@example.com")).toBeInTheDocument()
  })

  it("renders API keys section with all providers", () => {
    render(<SettingsPage />)
    expect(screen.getByText("API Keys")).toBeInTheDocument()
    expect(screen.getByText("Financial Modeling Prep")).toBeInTheDocument()
    expect(screen.getByText("Polygon.io")).toBeInTheDocument()
    expect(screen.getByText("Finnhub")).toBeInTheDocument()
    expect(screen.getByText("FRED")).toBeInTheDocument()
  })

  it("renders save buttons for each provider", () => {
    render(<SettingsPage />)
    const saveButtons = screen.getAllByText("Save")
    expect(saveButtons).toHaveLength(4)
  })
})
