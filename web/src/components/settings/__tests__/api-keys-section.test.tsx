import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ApiKeysSection } from "../api-keys-section"

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe("ApiKeysSection", () => {
  it("shows upgrade CTA when subscription is free", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })

    render(<ApiKeysSection />)
    expect(await screen.findByRole("button", { name: /upgrade/i })).toBeInTheDocument()
  })

  it("shows key management when subscription is active", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ keys: [] }),
      })

    render(<ApiKeysSection />)
    expect(await screen.findByRole("heading", { name: /API Keys/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /upgrade/i })).not.toBeInTheDocument()
  })

  it("renders existing keys as masked", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            keys: [
              {
                id: 1,
                provider_name: "fmp",
                masked_key: "****abc123",
                is_platform_managed: false,
                created_at: "2026-01-01T00:00:00Z",
              },
            ],
          }),
      })

    render(<ApiKeysSection />)
    expect(await screen.findByText("****abc123")).toBeInTheDocument()
  })
})
