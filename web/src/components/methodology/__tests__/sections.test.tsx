import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    h4: ({ children, ...props }: any) => <h4 {...props}>{children}</h4>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
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

import { HeroSection } from "../sections/hero-section"
import { PipelineSection } from "../sections/pipeline-section"
import { UniverseSection } from "../sections/universe-section"
import { FiltersSection } from "../sections/filters-section"

describe("HeroSection", () => {
  it("renders the H1 headline", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(/From 7,000\+ stocks to the ones worth your attention/)
    ).toBeInTheDocument()
  })

  it("renders outcome bullets", () => {
    render(<HeroSection />)
    expect(screen.getByText("Scores updated daily after market close")).toBeInTheDocument()
    expect(screen.getByText("Position sizing tied to conviction strength")).toBeInTheDocument()
  })

  it("renders built-for and not-built-for cards", () => {
    render(<HeroSection />)
    expect(screen.getByText("Built for")).toBeInTheDocument()
    expect(screen.getByText("Not built for")).toBeInTheDocument()
  })
})

describe("PipelineSection", () => {
  it("renders the headline", () => {
    render(<PipelineSection />)
    expect(
      screen.getByText(/From raw data to conviction/)
    ).toBeInTheDocument()
  })

  it("renders all 6 pipeline stages", () => {
    render(<PipelineSection />)
    expect(screen.getAllByText("Universe").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Filters").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Scoring").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Conviction").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Output").length).toBeGreaterThan(0)
  })
})

describe("UniverseSection", () => {
  it("renders the headline", () => {
    render(<UniverseSection />)
    expect(
      screen.getByText(/Every US-listed equity/)
    ).toBeInTheDocument()
  })

  it("renders all three cards", () => {
    render(<UniverseSection />)
    expect(screen.getByText(/What\u2019s included/)).toBeInTheDocument()
    expect(screen.getByText(/What\u2019s excluded/)).toBeInTheDocument()
    expect(screen.getByText("Data freshness")).toBeInTheDocument()
  })
})

describe("FiltersSection", () => {
  it("renders the headline", () => {
    render(<FiltersSection />)
    expect(
      screen.getByText(/Bad candidates are removed before scoring begins/)
    ).toBeInTheDocument()
  })

  it("renders all six filter cards", () => {
    render(<FiltersSection />)
    expect(screen.getByText("Liquidity")).toBeInTheDocument()
    expect(screen.getByText("Earnings Quality")).toBeInTheDocument()
    expect(screen.getByText("Bankruptcy Risk")).toBeInTheDocument()
    expect(screen.getByText("Cash Flow")).toBeInTheDocument()
    expect(screen.getByText("Interest Coverage")).toBeInTheDocument()
    expect(screen.getByText("Balance Sheet Health")).toBeInTheDocument()
  })
})
