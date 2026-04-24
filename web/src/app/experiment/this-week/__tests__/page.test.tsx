import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  })
})

const mockCapture = vi.fn()
vi.mock("posthog-js", () => ({
  default: { capture: mockCapture },
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { CheckoutButton } from "../checkout-button"

describe("CheckoutButton", () => {
  it("renders the purchase button", () => {
    render(<CheckoutButton />)
    const button = screen.getByRole("button", { name: /get this week/i })
    expect(button).toBeInTheDocument()
  })

  it("fires checkout_click PostHog event on click", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ checkout_url: "https://checkout.stripe.com/test" }),
    })

    // Mock window.location.href setter
    const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      href: "",
      origin: "http://localhost:3000",
    } as Location)

    render(<CheckoutButton />)
    const button = screen.getByRole("button", { name: /get this week/i })
    fireEvent.click(button)

    expect(mockCapture).toHaveBeenCalledWith("checkout_click", {
      experiment: "ten_dollar_list",
      amount_cents: 1000,
    })

    locationSpy.mockRestore()
  })
})
