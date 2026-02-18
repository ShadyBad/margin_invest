import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

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
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  LineChart: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
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
  it("renders all 9 sections", async () => {
    const jsx = await Page()
    render(jsx)

    // Hero
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()

    // Problem
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()

    // Pipeline
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()

    // Engine cards (appear in both desktop + mobile layouts)
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)

    // Proof
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()

    // Positioning
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()

    // Pricing
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()

    // Infrastructure (NEW)
    expect(screen.getByText(/institutional-grade infrastructure/i)).toBeInTheDocument()

    // Footer (engine version also appears in hero card metadata)
    expect(screen.getAllByText(/engine v1\.3\.2/i).length).toBeGreaterThanOrEqual(1)
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })
})
