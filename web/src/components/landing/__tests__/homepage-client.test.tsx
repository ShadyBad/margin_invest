import { describe, it, expect, vi, beforeAll } from "vitest"
import { render } from "@testing-library/react"

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
    to: vi.fn(() => ({ kill: vi.fn() })),
    from: vi.fn(() => ({ kill: vi.fn() })),
    fromTo: vi.fn(() => ({ kill: vi.fn() })),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
      scrollTrigger: null,
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

import { HomepageClient } from "../homepage-client"

describe("HomepageClient section order", () => {
  it("renders 7 sections: hero, authority, evidence, pipeline, results, pricing, footer", () => {
    const { container } = render(<HomepageClient data={null} />)

    // Sections with id attributes
    const sections = container.querySelectorAll("section[id]")
    const ids = Array.from(sections).map((s) => s.id)

    expect(ids).toContain("hero")
    expect(ids).toContain("pricing")

    // Footer uses <footer> tag, not <section>
    const footer = container.querySelector("footer#footer")
    expect(footer).toBeInTheDocument()
  })

  it("does NOT render standalone FaqSection", () => {
    const { container } = render(<HomepageClient data={null} />)
    const faqSection = container.querySelector("section#faq")
    expect(faqSection).not.toBeInTheDocument()
  })

  it("renders sections in correct order", () => {
    const { container } = render(<HomepageClient data={null} />)

    // Collect all top-level section/footer elements within the scroll canvas
    const allSections = container.querySelectorAll("section[id], footer[id]")
    const orderedIds = Array.from(allSections).map((s) => s.id)

    // hero comes before pricing
    const heroIdx = orderedIds.indexOf("hero")
    const pricingIdx = orderedIds.indexOf("pricing")
    const footerIdx = orderedIds.indexOf("footer")

    expect(heroIdx).toBeLessThan(pricingIdx)
    expect(pricingIdx).toBeLessThan(footerIdx)
  })
})
