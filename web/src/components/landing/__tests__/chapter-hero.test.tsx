import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0 } }),
  useTransform: () => ({ get: () => 1 }),
  useMotionValueEvent: vi.fn(),
}))

import { ChapterHero } from "../chapter-hero"

describe("ChapterHero", () => {
  it("renders headline text", () => {
    const { container } = render(<ChapterHero />)
    const h1 = container.querySelector("h1")
    expect(h1).toBeDefined()
    expect(h1?.textContent).toContain("Conviction")
    expect(h1?.textContent).toContain("Quantified")
  })

  it("renders primary CTA button", () => {
    const { getByRole } = render(<ChapterHero />)
    const cta = getByRole("link", { name: /start scoring/i })
    expect(cta).toBeDefined()
  })

  it("renders secondary CTA", () => {
    const { getByRole } = render(<ChapterHero />)
    const secondary = getByRole("link", { name: /see how it works/i })
    expect(secondary).toBeDefined()
  })

  it("renders scroll indicator", () => {
    const { container } = render(<ChapterHero />)
    const indicator = container.querySelector("[data-scroll-indicator]")
    expect(indicator).toBeDefined()
  })
})
