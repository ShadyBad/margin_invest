import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useSubscriptionTier } from "../use-subscription-tier"

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("useSubscriptionTier", () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it("returns 'free' when billing status is inactive", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })
    const { result } = renderHook(() => useSubscriptionTier())
    expect(result.current.tier).toBe("free") // default before fetch
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("free")
  })

  it("returns 'pro' when billing status is active", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
    })
    const { result } = renderHook(() => useSubscriptionTier())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("pro")
  })

  it("returns 'free' on fetch error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network"))
    const { result } = renderHook(() => useSubscriptionTier())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("free")
  })
})
