import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

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
      expect(screen.getByText("Manage subscription")).toBeInTheDocument()
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
})
