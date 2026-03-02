import { describe, it, expect, vi } from "vitest"

const mockRedirect = vi.fn()

vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => {
    mockRedirect(...args)
    throw new Error("NEXT_REDIRECT")
  },
}))

describe("Settings Page", () => {
  it("redirects to /account", async () => {
    const { default: SettingsPage } = await import("../page")
    expect(() => SettingsPage()).toThrow("NEXT_REDIRECT")
    expect(mockRedirect).toHaveBeenCalledWith("/account")
  })
})
