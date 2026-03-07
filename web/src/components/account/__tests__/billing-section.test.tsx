import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { BillingSection } from "../billing-section"

function mockBillingFetch(response: Record<string, unknown>) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(response),
  })
}

describe("BillingSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows loading skeleton initially", () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {})) // never resolves
    render(<BillingSection />)
    expect(screen.getByRole("heading", { name: /billing/i })).toBeInTheDocument()
    expect(screen.getByText("Billing").closest("section")!.querySelector(".animate-pulse")).toBeTruthy()
  })

  it("shows Analyst plan badge", async () => {
    mockBillingFetch({
      plan: "analyst",
      status: null,
      current_period_end: null,
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Analyst")).toBeInTheDocument()
    })
  })

  it("shows Portfolio plan badge with Active status", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Portfolio")).toBeInTheDocument()
      expect(screen.getByText("Active")).toBeInTheDocument()
    })
  })

  it("shows Institutional plan badge with Active status", async () => {
    mockBillingFetch({
      plan: "institutional",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Institutional")).toBeInTheDocument()
      expect(screen.getByText("Active")).toBeInTheDocument()
    })
  })

  it("disables action buttons when Stripe is not configured", async () => {
    mockBillingFetch({
      plan: "analyst",
      status: null,
      current_period_end: null,
      is_active: true,
      billing_configured: false,
    })
    render(<BillingSection />)
    await waitFor(() => {
      const portfolioBtn = screen.getByText("Upgrade to Portfolio - $29/mo")
      const institutionalBtn = screen.getByText("Upgrade to Institutional - $79/mo")
      expect(portfolioBtn.closest("button")).toBeDisabled()
      expect(institutionalBtn.closest("button")).toBeDisabled()
    })
  })

  it("shows upgrade buttons for Analyst users", async () => {
    mockBillingFetch({
      plan: "analyst",
      status: null,
      current_period_end: null,
      is_active: true,
      billing_configured: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Upgrade to Portfolio - $29/mo")).toBeInTheDocument()
      expect(screen.getByText("Upgrade to Institutional - $79/mo")).toBeInTheDocument()
    })
  })

  it("shows manage subscription button for paid users", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
      billing_configured: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription →")).toBeInTheDocument()
    })
  })

  it("shows renewal date for active subscription", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "active",
      current_period_end: "2026-04-15T12:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText(/Renews/)).toBeInTheDocument()
      expect(screen.getByText(/April 15, 2026/)).toBeInTheDocument()
    })
  })

  it('shows "Access until" for canceled subscription', async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "canceled",
      current_period_end: "2026-05-15T12:00:00Z",
      is_active: false,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText(/Access until/)).toBeInTheDocument()
      expect(screen.getByText(/May 15, 2026/)).toBeInTheDocument()
      expect(screen.getByText("Canceled")).toBeInTheDocument()
    })
  })

  it("shows error message when billing API fails", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Unable to load billing information.")).toBeInTheDocument()
    })
  })

  it("shows past due warning", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "past_due",
      current_period_end: "2026-03-01T00:00:00Z",
      is_active: true,
      billing_configured: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Past Due")).toBeInTheDocument()
      expect(screen.getByText(/payment method needs updating/)).toBeInTheDocument()
      expect(screen.getByText("Update payment method")).toBeInTheDocument()
    })
  })

  it("shows explanation when billing is not configured", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
      billing_configured: false,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText(/Billing is not yet available/)).toBeInTheDocument()
    })
  })

  it("does not show billing explanation when billing is configured", async () => {
    mockBillingFetch({
      plan: "portfolio",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
      billing_configured: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription →")).toBeInTheDocument()
    })
    expect(screen.queryByText(/Billing is not yet available/)).not.toBeInTheDocument()
  })

  it("shows error when portal request fails with non-ok response", async () => {
    const user = userEvent.setup()
    // First call: billing status (ok), second call: portal (fails)
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            plan: "portfolio",
            status: "active",
            current_period_end: "2026-04-01T00:00:00Z",
            is_active: true,
            billing_configured: true,
          }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ message: "No Stripe customer found" }),
      })

    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription →")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Manage subscription →"))

    await waitFor(() => {
      expect(screen.getByText("No Stripe customer found")).toBeInTheDocument()
    })
  })

  it("shows error when portal request throws a network error", async () => {
    const user = userEvent.setup()
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            plan: "portfolio",
            status: "active",
            current_period_end: "2026-04-01T00:00:00Z",
            is_active: true,
            billing_configured: true,
          }),
      })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))

    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription →")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Manage subscription →"))

    await waitFor(() => {
      expect(screen.getByText("Failed to fetch")).toBeInTheDocument()
    })
  })

  it("shows error when checkout request fails", async () => {
    const user = userEvent.setup()
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            plan: "analyst",
            status: null,
            current_period_end: null,
            is_active: true,
            billing_configured: true,
          }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: () => Promise.resolve({ message: "Failed to create checkout session" }),
      })

    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Upgrade to Portfolio - $29/mo")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Upgrade to Portfolio - $29/mo"))

    await waitFor(() => {
      expect(screen.getByText("Failed to create checkout session")).toBeInTheDocument()
    })
  })

  it("clears action error when retrying", async () => {
    const user = userEvent.setup()
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            plan: "portfolio",
            status: "active",
            current_period_end: "2026-04-01T00:00:00Z",
            is_active: true,
            billing_configured: true,
          }),
      })
      // First portal click: fails
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ message: "Internal error" }),
      })
      // Second portal click: succeeds
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ portal_url: "https://billing.stripe.com/session/test" }),
      })

    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription →")).toBeInTheDocument()
    })

    // First click — error
    await user.click(screen.getByText("Manage subscription →"))
    await waitFor(() => {
      expect(screen.getByText("Internal error")).toBeInTheDocument()
    })

    // Second click — error should clear
    await user.click(screen.getByText("Manage subscription →"))
    await waitFor(() => {
      expect(screen.queryByText("Internal error")).not.toBeInTheDocument()
    })
  })
})
