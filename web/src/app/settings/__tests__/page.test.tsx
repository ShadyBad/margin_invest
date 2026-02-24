import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// The settings page is now a server component. We test the gutted version
// by rendering a simplified client-side version of the component.

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
  usePathname: () => "/settings",
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue({ user: { name: "Test" } }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { user: { name: "Test" } },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

describe("Settings Page (gutted)", () => {
  it("renders the settings heading and placeholder text", async () => {
    // Since the page is a server component, we test the markup directly
    const { default: SettingsPage } = await import("../page")
    const result = await SettingsPage()
    render(result)
    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument()
    expect(screen.getByText("Product preferences coming soon.")).toBeInTheDocument()
  })
})
