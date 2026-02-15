import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { BillingSection } from "../billing-section"

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("BillingSection", () => {
  it("shows free plan with upgrade button", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })
    render(<BillingSection />)
    expect(await screen.findByText(/Free/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /upgrade/i })).toBeInTheDocument()
  })

  it("shows active plan with manage button", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          subscription_plan: "margin_invest",
          is_active: true,
          stripe_subscription_id: "sub_123",
        }),
    })
    render(<BillingSection />)
    expect(await screen.findByText(/Margin Invest/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /manage/i })).toBeInTheDocument()
  })
})
