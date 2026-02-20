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

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  ReferenceLine: () => null,
  Tooltip: () => null,
}))

import { HeroSection } from "../sections/hero-section"
import { PipelineSection } from "../sections/pipeline-section"
import { UniverseSection } from "../sections/universe-section"
import { FiltersSection } from "../sections/filters-section"
import { ScoringSection } from "../sections/scoring-section"
import { ConvictionSection } from "../sections/conviction-section"
import { OutputsSection } from "../sections/outputs-section"
import { UsageSection } from "../sections/usage-section"
import { TransparencySection } from "../sections/transparency-section"
import { CTASection } from "../sections/cta-section"

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

describe("ScoringSection", () => {
  it("renders the headline", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/20\+ factors\. Three pillars\. Sector-neutral ranking\./)
    ).toBeInTheDocument()
  })

  it("renders all three pillars", () => {
    render(<ScoringSection />)
    expect(screen.getAllByText("Quality").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Value").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Momentum").length).toBeGreaterThanOrEqual(1)
  })

  it("renders named sub-factors", () => {
    render(<ScoringSection />)
    expect(screen.getByText("ROIC-WACC Spread")).toBeInTheDocument()
    expect(screen.getByText("Piotroski F-Score")).toBeInTheDocument()
    expect(screen.getByText("Insider Cluster Score")).toBeInTheDocument()
  })
})

describe("ConvictionSection", () => {
  it("renders the headline", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Two independent lenses/)
    ).toBeInTheDocument()
  })

  it("renders both track cards", () => {
    render(<ConvictionSection />)
    expect(screen.getByText(/Track A/)).toBeInTheDocument()
    expect(screen.getByText(/Track B/)).toBeInTheDocument()
  })

  it("renders conviction levels", () => {
    render(<ConvictionSection />)
    expect(screen.getAllByText("Exceptional").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("High").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Watchlist").length).toBeGreaterThanOrEqual(1)
  })
})

describe("OutputsSection", () => {
  it("renders the headline", () => {
    render(<OutputsSection />)
    expect(
      screen.getByText(/Structured outputs you can act on/)
    ).toBeInTheDocument()
  })

  it("renders all four output cards", () => {
    render(<OutputsSection />)
    expect(screen.getByText("Candidate cards")).toBeInTheDocument()
    expect(screen.getByText("Factor breakdown")).toBeInTheDocument()
    expect(screen.getByText("Price target framework")).toBeInTheDocument()
    expect(screen.getByText("Position sizing")).toBeInTheDocument()
  })
})

describe("UsageSection", () => {
  it("renders the headline", () => {
    render(<UsageSection />)
    expect(
      screen.getByText(/What to do — and not do/)
    ).toBeInTheDocument()
  })

  it("renders do and don't items", () => {
    render(<UsageSection />)
    expect(screen.getByText(/Use candidates as a starting point/)).toBeInTheDocument()
    expect(screen.getByText(/Don\u2019t treat a high conviction score/)).toBeInTheDocument()
  })
})

describe("TransparencySection", () => {
  it("renders the headline", () => {
    render(<TransparencySection />)
    expect(
      screen.getByText(/What this is — and what it isn't/)
    ).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Not financial advice")).toBeInTheDocument()
    expect(screen.getByText("Models have limits")).toBeInTheDocument()
    expect(screen.getByText("Structure, not prediction")).toBeInTheDocument()
  })

  it("renders the validation checklist", () => {
    render(<TransparencySection />)
    expect(screen.getByText(/Before acting on any candidate/)).toBeInTheDocument()
    expect(screen.getByText(/Does the thesis make sense/)).toBeInTheDocument()
  })
})

describe("CTASection", () => {
  it("renders the headline", () => {
    render(<CTASection />)
    expect(
      screen.getByText(/Replace hours of screening/)
    ).toBeInTheDocument()
  })

  it("renders both comparison cards", () => {
    render(<CTASection />)
    expect(screen.getByText("Without a system")).toBeInTheDocument()
    expect(screen.getByText("With Margin Invest")).toBeInTheDocument()
  })

  it("renders CTA links", () => {
    render(<CTASection />)
    expect(
      screen.getByRole("link", { name: /Score your first stock free/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /Compare plans/i })
    ).toBeInTheDocument()
  })
})
