// web/src/components/landing/__tests__/page-assembly.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock FluidShaderLoader to render nothing (WebGL can't render in jsdom)
vi.mock("@/components/landing/fluid-shader-loader", () => ({
  FluidShaderLoader: () => null,
}))

// Mock auth to return null (unauthenticated)
vi.mock("@/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue(null),
}))

// Mock next-auth/react for Navbar
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

// Mock next/navigation for Navbar
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}))

// Mock framer-motion
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
  useReducedMotion: () => false,
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all 4 chapters", async () => {
    const jsx = await Page()
    render(jsx)
    // Chapter 1: Hero (WordReveal splits text into individual <span> words)
    expect(screen.getByText("Conviction,")).toBeInTheDocument()
    expect(screen.getByText("Quantified.")).toBeInTheDocument()
    // Chapter 2: Engine
    expect(screen.getByText("Raw Signal")).toBeInTheDocument()
    expect(screen.getByText("Structured Analysis")).toBeInTheDocument()
    expect(screen.getByText("Conviction Output")).toBeInTheDocument()
    // Chapter 3: Proof
    expect(screen.getByText("Sample Analysis")).toBeInTheDocument()
    expect(screen.getByText("Factor Depth")).toBeInTheDocument()
    expect(screen.getByText("Portfolio View")).toBeInTheDocument()
    // Chapter 4: Path (pricing)
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

  it("renders chapter breaks between sections", async () => {
    const jsx = await Page()
    const { container } = render(jsx)
    const breaks = container.querySelectorAll(".h-\\[50vh\\]")
    expect(breaks.length).toBe(3)
  })

  it("renders chapter indicator", async () => {
    const jsx = await Page()
    render(jsx)
    expect(screen.getByLabelText("Page chapters")).toBeInTheDocument()
  })
})
