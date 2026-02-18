import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/components/landing/fluid-shader-loader", () => ({
  FluidShaderLoader: () => null,
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
    section: ({ children, ...props }: any) => (
      <section {...props}>{children}</section>
    ),
  },
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, inputOrFn: number[] | Function, output?: any[]) => {
    if (typeof inputOrFn === "function") return inputOrFn(0)
    return output![Math.floor(output!.length / 2)]
  },
  useReducedMotion: () => false,
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all 3 chapters", async () => {
    const jsx = await Page()
    render(jsx)
    // Chapter 1: Hero
    expect(screen.getByText("Conviction,")).toBeInTheDocument()
    expect(screen.getByText("Quantified.")).toBeInTheDocument()
    // Chapter 2: Counter-flow cards (engine + proof)
    // Use getAllByText because jsdom renders both desktop and mobile layouts
    expect(screen.getAllByText("Raw Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Factor Analysis").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Sample Score").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio View").length).toBeGreaterThanOrEqual(1)
    // Chapter 3: Pricing
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("Allocator")).toBeInTheDocument()
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })

  it("has no 50vh chapter break spacers", async () => {
    const jsx = await Page()
    const { container } = render(jsx)
    const breaks = container.querySelectorAll(".h-\\[50vh\\]")
    expect(breaks.length).toBe(0)
  })

  it("renders chapter indicator with 3 chapters", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByLabelText("Page chapters")
    expect(nav).toBeInTheDocument()
    // Should have 3 dots, not 4
    const dots = nav.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(3)
  })
})
