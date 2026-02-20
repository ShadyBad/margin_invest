import { describe, it, expect, vi } from "vitest"

const mockRedirect = vi.fn()

vi.mock("next/navigation", () => ({
  redirect: mockRedirect,
}))

describe("Register Page", () => {
  it("redirects to /login?mode=signup", async () => {
    const { default: RegisterPage } = await import("../page")
    try {
      RegisterPage()
    } catch {
      // redirect() throws in test environment
    }
    expect(mockRedirect).toHaveBeenCalledWith("/login?mode=signup")
  })
})
