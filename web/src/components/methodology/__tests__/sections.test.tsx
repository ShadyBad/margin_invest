import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

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
  useMotionValue: (init: number) => ({
    get: () => init,
    set: () => {},
    on: () => () => {},
  }),
  useTransform: () => ({
    get: () => "0",
    on: () => () => {},
  }),
  useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => () => {} } }),
  animate: () => ({ stop: () => {} }),
}))

import {
  MethodologyHero,
  PipelineSection,
  FactorSection,
  TransparencySection,
  MethodologyCTA,
} from "../index"

describe("MethodologyHero", () => {
  it("renders the headline", () => {
    render(<MethodologyHero />)
    expect(screen.getByText("How Margin scores equities.")).toBeInTheDocument()
  })

  it("renders the description", () => {
    render(<MethodologyHero />)
    expect(screen.getByText(/deterministic pipeline/i)).toBeInTheDocument()
  })
})

describe("PipelineSection", () => {
  it("renders the section label", () => {
    render(<PipelineSection />)
    expect(screen.getByText("The Pipeline")).toBeInTheDocument()
  })

  it("renders all four pipeline stages", () => {
    render(<PipelineSection />)
    expect(screen.getAllByText("Market Data").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Factor Scoring").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Composite Output").length).toBeGreaterThanOrEqual(1)
  })
})

describe("FactorSection", () => {
  it("renders the heading", () => {
    render(<FactorSection />)
    expect(screen.getByText("Five factors. One score.")).toBeInTheDocument()
  })

  it("renders all five factors", () => {
    render(<FactorSection />)
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
    expect(screen.getByText("Stability")).toBeInTheDocument()
  })
})

describe("TransparencySection", () => {
  it("renders the heading", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Structure you can verify.")).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Deterministic")).toBeInTheDocument()
    expect(screen.getByText("Sector-Neutral")).toBeInTheDocument()
    expect(screen.getByText("Transparent")).toBeInTheDocument()
  })
})

describe("MethodologyCTA", () => {
  it("renders the CTA heading and button", () => {
    render(<MethodologyCTA />)
    expect(screen.getByText("See it in action.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<MethodologyCTA />)
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
