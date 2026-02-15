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

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("Settings Page", () => {
  beforeEach(() => {
    mockFetch.mockReset()
    // Default: billing status returns active plan, keys endpoint returns empty
    mockFetch.mockImplementation((url: string) => {
      if (url === "/api/v1/billing/status") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              subscription_plan: "margin_invest",
              is_active: true,
              stripe_subscription_id: "sub_123",
            }),
        })
      }
      if (url === "/api/v1/keys/") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ keys: [] }),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

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

  it("renders billing section", async () => {
    render(<SettingsPage />)
    expect(await screen.findByRole("heading", { name: "Billing" })).toBeInTheDocument()
    expect(await screen.findByRole("button", { name: /manage/i })).toBeInTheDocument()
  })

  it("renders API keys section", async () => {
    render(<SettingsPage />)
    expect(await screen.findByRole("heading", { name: /API Keys/i })).toBeInTheDocument()
  })
})
