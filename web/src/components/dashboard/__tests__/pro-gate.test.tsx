import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ProGate } from "../pro-gate"

// Mock the hook
vi.mock("@/lib/hooks/use-subscription-tier", () => ({
  useSubscriptionTier: vi.fn(),
}))

import { useSubscriptionTier } from "@/lib/hooks/use-subscription-tier"
const mockHook = vi.mocked(useSubscriptionTier)

describe("ProGate", () => {
  it("renders children unblurred for pro users", () => {
    mockHook.mockReturnValue({ tier: "pro", loading: false })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    expect(screen.getByTestId("content")).toBeVisible()
    expect(screen.queryByText(/unlock/i)).not.toBeInTheDocument()
  })

  it("renders children with blur overlay for free users", () => {
    mockHook.mockReturnValue({ tier: "free", loading: false })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    const container = screen.getByTestId("pro-gate-overlay")
    expect(container).toBeInTheDocument()
    expect(container.className).toContain("blur")
  })

  it("shows lock icon and CTA for free users", () => {
    mockHook.mockReturnValue({ tier: "free", loading: false })
    render(
      <ProGate>
        <div>Secret data</div>
      </ProGate>
    )
    expect(screen.getByText(/unlock institutional-grade analytics/i)).toBeInTheDocument()
    expect(screen.getByText(/pro insight/i)).toBeInTheDocument()
  })

  it("renders children unblurred while loading", () => {
    mockHook.mockReturnValue({ tier: "free", loading: true })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    // Don't show blur while loading to avoid flash
    expect(screen.queryByTestId("pro-gate-overlay")).not.toBeInTheDocument()
  })
})
