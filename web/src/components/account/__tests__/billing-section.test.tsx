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

  it("shows Scout plan badge", async () => {
    mockBillingFetch({
      plan: "scout",
      status: null,
      current_period_end: null,
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Scout")).toBeInTheDocument()
    })
  })

  it("shows Operator plan badge with Active status", async () => {
    mockBillingFetch({
      plan: "operator",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Operator")).toBeInTheDocument()
      expect(screen.getByText("Active")).toBeInTheDocument()
    })
  })

  it("shows Allocator plan badge with Active status", async () => {
    mockBillingFetch({
      plan: "allocator",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Allocator")).toBeInTheDocument()
      expect(screen.getByText("Active")).toBeInTheDocument()
    })
  })

  it("shows upgrade buttons for Scout users", async () => {
    mockBillingFetch({
      plan: "scout",
      status: null,
      current_period_end: null,
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Upgrade to Operator - $29/mo")).toBeInTheDocument()
      expect(screen.getByText("Upgrade to Allocator - $79/mo")).toBeInTheDocument()
    })
  })

  it("shows manage subscription button for paid users", async () => {
    mockBillingFetch({
      plan: "operator",
      status: "active",
      current_period_end: "2026-04-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Manage subscription")).toBeInTheDocument()
    })
  })

  it("shows renewal date for active subscription", async () => {
    mockBillingFetch({
      plan: "operator",
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
      plan: "operator",
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
      plan: "operator",
      status: "past_due",
      current_period_end: "2026-03-01T00:00:00Z",
      is_active: true,
    })
    render(<BillingSection />)
    await waitFor(() => {
      expect(screen.getByText("Past Due")).toBeInTheDocument()
      expect(screen.getByText(/payment method needs updating/)).toBeInTheDocument()
      expect(screen.getByText("Update payment method")).toBeInTheDocument()
    })
  })
})
