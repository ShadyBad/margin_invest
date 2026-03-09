import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"

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

vi.mock("@/lib/api/server", () => ({
  serverFetch: vi.fn().mockResolvedValue({ picks: [], last_updated: "", total_scored: 0, universe: null, watchlist: [], warnings: [] }),
}))
vi.mock("@/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue(null),
}))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("gsap/ScrollSmoother", () => ({
  default: { create: vi.fn(() => ({ kill: vi.fn() })) },
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Cell: () => null,
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders core sections", async () => {
    const jsx = await Page()
    render(jsx)

    // Hero
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()

    // Pricing
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()

    // Hero search (appears in hero + FAQ closing CTA)
    const searchInputs = screen.getAllByPlaceholderText(/search any ticker/i)
    expect(searchInputs.length).toBeGreaterThanOrEqual(1)
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })
})
