import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api/server", () => ({
  serverFetch: vi.fn().mockResolvedValue({ picks: [] }),
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

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
  },
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, inputOrFn: number[] | Function, output?: any[]) => {
    if (typeof inputOrFn === "function") return inputOrFn(0)
    return output![Math.floor(output!.length / 2)]
  },
  useReducedMotion: () => false,
}))

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn() },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [] },
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all major sections", async () => {
    const jsx = await Page()
    render(jsx)

    // Hero
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()

    // Problem
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()

    // Engine - cards appear twice (desktop + mobile), use getAllByText
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)

    // Pipeline
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()

    // Proof
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()

    // Positioning
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()

    // Pricing (renamed tiers)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()

    // Legitimacy
    expect(screen.getByText(/no hidden heuristics/i)).toBeInTheDocument()

    // Footer
    expect(screen.getByText(/engine v/i)).toBeInTheDocument()
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })
})
