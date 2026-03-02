import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

type MockProps = Record<string, unknown> & { children?: React.ReactNode }

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: MockProps) => <div {...props as React.HTMLAttributes<HTMLDivElement>}>{children}</div>,
    h1: ({ children, ...props }: MockProps) => <h1 {...props as React.HTMLAttributes<HTMLHeadingElement>}>{children}</h1>,
    h2: ({ children, ...props }: MockProps) => <h2 {...props as React.HTMLAttributes<HTMLHeadingElement>}>{children}</h2>,
    h3: ({ children, ...props }: MockProps) => <h3 {...props as React.HTMLAttributes<HTMLHeadingElement>}>{children}</h3>,
    h4: ({ children, ...props }: MockProps) => <h4 {...props as React.HTMLAttributes<HTMLHeadingElement>}>{children}</h4>,
    p: ({ children, ...props }: MockProps) => <p {...props as React.HTMLAttributes<HTMLParagraphElement>}>{children}</p>,
    span: ({ children, ...props }: MockProps) => <span {...props as React.HTMLAttributes<HTMLSpanElement>}>{children}</span>,
    ul: ({ children, ...props }: MockProps) => <ul {...props as React.HTMLAttributes<HTMLUListElement>}>{children}</ul>,
    section: ({ children, ...props }: MockProps) => (
      <section {...props as React.HTMLAttributes<HTMLElement>}>{children}</section>
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
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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
import { MLRefinementSection } from "../sections/ml-refinement-section"
import { SmartMoneySection } from "../sections/smart-money-section"
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

  it("renders narrative subhead about following one stock", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(/Follow one stock through our entire pipeline/)
    ).toBeInTheDocument()
  })

  it("renders the V4 pipeline badge", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(/Pipeline V4 · Updated February 2026/)
    ).toBeInTheDocument()
  })

  it("renders outcome bullets", () => {
    render(<HeroSection />)
    expect(screen.getByText("Scores updated daily after market close")).toBeInTheDocument()
    expect(screen.getByText("Position sizing tied to composite tier strength")).toBeInTheDocument()
  })

  it("renders CTA links", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /Explore dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Read guides/i })).toBeInTheDocument()
  })
})

describe("PipelineSection", () => {
  it("renders the headline", () => {
    render(<PipelineSection />)
    expect(
      screen.getByText(/Seven stages\. One stock at a time\./)
    ).toBeInTheDocument()
  })

  it("renders narrative about following AAPL", () => {
    render(<PipelineSection />)
    expect(
      screen.getByText(/follow Apple \(AAPL\) through the pipeline/)
    ).toBeInTheDocument()
  })

  it("renders all 7 pipeline stages including ML and Smart Money", () => {
    render(<PipelineSection />)
    // "Universe" appears in both stage cards and PipelineDiagram visual
    expect(screen.getAllByText("Universe").length).toBeGreaterThan(0)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Factor Scoring")).toBeInTheDocument()
    expect(screen.getByText("Dual-Track Scoring")).toBeInTheDocument()
    expect(screen.getByText("ML Refinement")).toBeInTheDocument()
    expect(screen.getByText("Smart Money Overlay")).toBeInTheDocument()
    expect(screen.getByText("Position Sizing")).toBeInTheDocument()
  })
})

describe("UniverseSection", () => {
  it("renders the headline with 7,000+", () => {
    render(<UniverseSection />)
    expect(
      screen.getByText(/the pipeline starts with 7,000\+ stocks/)
    ).toBeInTheDocument()
  })

  it("renders narrative mentioning AAPL and elimination filters", () => {
    render(<UniverseSection />)
    expect(
      screen.getByText(/AAPL is one of them/)
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
  it("renders the headline about binary checks", () => {
    render(<FiltersSection />)
    expect(
      screen.getByText(/Six binary checks\. One failure means elimination\./)
    ).toBeInTheDocument()
  })

  it("renders narrative mentioning AAPL", () => {
    render(<FiltersSection />)
    expect(
      screen.getByText(/AAPL faces six binary pass\/fail checks/)
    ).toBeInTheDocument()
  })

  it("renders all six filter names", () => {
    render(<FiltersSection />)
    expect(screen.getByText("Beneish M-Score")).toBeInTheDocument()
    expect(screen.getByText("Altman Z-Score")).toBeInTheDocument()
    expect(screen.getByText("Current Ratio")).toBeInTheDocument()
    expect(screen.getByText("Interest Coverage")).toBeInTheDocument()
    expect(screen.getByText("FCF Distress")).toBeInTheDocument()
    expect(screen.getByText("Liquidity")).toBeInTheDocument()
  })

  it("renders AAPL result callout", () => {
    render(<FiltersSection />)
    expect(
      screen.getByText(/AAPL passes all six filters and advances to scoring/)
    ).toBeInTheDocument()
  })
})

describe("ScoringSection", () => {
  it("renders the stage label", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/Stage 3 · Factor Scoring/)
    ).toBeInTheDocument()
  })

  it("renders the headline", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/17 factors\. Three pillars\. Sector-neutral ranking\./)
    ).toBeInTheDocument()
  })

  it("renders AAPL narrative", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/AAPL passed all filters/)
    ).toBeInTheDocument()
  })

  it("renders all three pillars with factor counts", () => {
    render(<ScoringSection />)
    expect(screen.getAllByText("Quality").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Value").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Momentum").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("6 factors")).toBeInTheDocument()
    expect(screen.getByText("7 factors")).toBeInTheDocument()
    expect(screen.getByText("4 factors")).toBeInTheDocument()
  })

  it("renders percentile ranking explanation", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/a percentile of 85 means AAPL scores better than 85%/)
    ).toBeInTheDocument()
  })
})

describe("ConvictionSection", () => {
  it("renders the stage label", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Stage 4 · Multi-Track Scoring/)
    ).toBeInTheDocument()
  })

  it("renders the headline", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Three independent tracks/)
    ).toBeInTheDocument()
  })

  it("renders AAPL narrative about multiplicative scoring", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/one weak gate kills the score/)
    ).toBeInTheDocument()
  })

  it("renders all three track cards with gates", () => {
    render(<ConvictionSection />)
    expect(screen.getByText(/Track A/)).toBeInTheDocument()
    expect(screen.getByText(/Track B/)).toBeInTheDocument()
    expect(screen.getByText(/Track C/)).toBeInTheDocument()
    expect(screen.getByText("Moat Evidence")).toBeInTheDocument()
    expect(screen.getByText("Reinvestment Engine")).toBeInTheDocument()
    expect(screen.getByText("Capital Allocation")).toBeInTheDocument()
    expect(screen.getByText("Ensemble Valuation")).toBeInTheDocument()
    expect(screen.getByText("Downside Protection")).toBeInTheDocument()
    expect(screen.getByText("Quality Floor")).toBeInTheDocument()
    expect(screen.getByText("Growth Efficiency")).toBeInTheDocument()
    expect(screen.getByText("Unit Economics")).toBeInTheDocument()
  })

  it("renders all four conviction levels with correct names", () => {
    render(<ConvictionSection />)
    expect(screen.getByText("EXCEPTIONAL")).toBeInTheDocument()
    expect(screen.getByText("HIGH")).toBeInTheDocument()
    expect(screen.getByText("MEDIUM")).toBeInTheDocument()
    expect(screen.getByText("NONE")).toBeInTheDocument()
  })

  it("mentions Track C is growth-only", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/growth-style companies only/)
    ).toBeInTheDocument()
  })
})

describe("MLRefinementSection", () => {
  it("renders the stage label", () => {
    render(<MLRefinementSection />)
    expect(
      screen.getByText(/Stage 5 · ML Refinement/)
    ).toBeInTheDocument()
  })

  it("renders the headline", () => {
    render(<MLRefinementSection />)
    expect(
      screen.getByText(/Deterministic first\. Machine learning second\./)
    ).toBeInTheDocument()
  })

  it("renders AAPL narrative", () => {
    render(<MLRefinementSection />)
    expect(
      screen.getByText(/deterministic scores are now refined by machine learning/)
    ).toBeInTheDocument()
  })

  it("renders all key points", () => {
    render(<MLRefinementSection />)
    expect(screen.getByText("Weekly training cycle")).toBeInTheDocument()
    expect(screen.getByText("Quality gate")).toBeInTheDocument()
    expect(screen.getByText("Cluster + anomaly detection")).toBeInTheDocument()
    expect(screen.getByText("Bounded adjustments")).toBeInTheDocument()
    expect(screen.getByText("Graceful degradation")).toBeInTheDocument()
  })

  it("renders the ML Adjusted badge callout", () => {
    render(<MLRefinementSection />)
    expect(screen.getByText("ML Adjusted")).toBeInTheDocument()
  })

  it("mentions rank IC threshold", () => {
    render(<MLRefinementSection />)
    expect(
      screen.getByText(/rank IC.*exceeds 0\.15/)
    ).toBeInTheDocument()
  })
})

describe("SmartMoneySection", () => {
  it("renders the stage label", () => {
    render(<SmartMoneySection />)
    expect(
      screen.getByText(/Stage 6 · Smart Money Overlay/)
    ).toBeInTheDocument()
  })

  it("renders the headline mentioning AAPL", () => {
    render(<SmartMoneySection />)
    expect(
      screen.getByText(/What institutional investors are doing with AAPL/)
    ).toBeInTheDocument()
  })

  it("renders all key points", () => {
    render(<SmartMoneySection />)
    expect(screen.getByText("13F filings")).toBeInTheDocument()
    expect(screen.getByText("Accumulation signals")).toBeInTheDocument()
    expect(screen.getByText("Curated manager list")).toBeInTheDocument()
    expect(screen.getByText("45-day reporting lag")).toBeInTheDocument()
  })

  it("renders the caveat about confirmation signal", () => {
    render(<SmartMoneySection />)
    expect(
      screen.getByText(/Institutional positioning is a confirmation signal/)
    ).toBeInTheDocument()
  })
})

describe("OutputsSection", () => {
  it("renders the stage label", () => {
    render(<OutputsSection />)
    expect(
      screen.getByText(/Stage 7 · Position Sizing/)
    ).toBeInTheDocument()
  })

  it("renders the headline about AAPL final output", () => {
    render(<OutputsSection />)
    expect(
      screen.getByText(/After all stages, AAPL receives its final output/)
    ).toBeInTheDocument()
  })

  it("renders example AAPL output", () => {
    render(<OutputsSection />)
    expect(screen.getByText("Composite Tier")).toBeInTheDocument()
    expect(screen.getByText("HIGH")).toBeInTheDocument()
    expect(screen.getByText("Compounder")).toBeInTheDocument()
    expect(screen.getByText("8%")).toBeInTheDocument()
  })

  it("renders factor breakdown percentiles", () => {
    render(<OutputsSection />)
    expect(screen.getByText("82nd")).toBeInTheDocument()
    expect(screen.getByText("64th")).toBeInTheDocument()
    expect(screen.getByText("71st")).toBeInTheDocument()
  })

  it("renders all four output field explanations", () => {
    render(<OutputsSection />)
    expect(screen.getByText("Composite tier")).toBeInTheDocument()
    expect(screen.getByText("Opportunity type")).toBeInTheDocument()
    expect(screen.getByText("Suggested position size")).toBeInTheDocument()
    expect(screen.getAllByText("Factor breakdown").length).toBeGreaterThanOrEqual(1)
  })
})

describe("UsageSection", () => {
  it("renders the headline", () => {
    render(<UsageSection />)
    expect(
      screen.getByText(/How to use these outputs/)
    ).toBeInTheDocument()
  })

  it("renders guide links", () => {
    render(<UsageSection />)
    expect(screen.getByText("Getting Started")).toBeInTheDocument()
    expect(screen.getByText("Reading the Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Scoring Factors")).toBeInTheDocument()
    expect(screen.getByText("Analyzing a Stock")).toBeInTheDocument()
  })

  it("renders guide links with correct hrefs", () => {
    render(<UsageSection />)
    expect(
      screen.getByRole("link", { name: /Getting Started/i })
    ).toHaveAttribute("href", "/guides/getting-started")
    expect(
      screen.getByRole("link", { name: /Scoring Factors/i })
    ).toHaveAttribute("href", "/guides/scoring-factors")
  })
})

describe("TransparencySection", () => {
  it("renders the headline about showing work", () => {
    render(<TransparencySection />)
    expect(
      screen.getByText(/We show our work because we trust our work/)
    ).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Deterministic")).toBeInTheDocument()
    expect(screen.getByText("Published formulas")).toBeInTheDocument()
    expect(screen.getByText("Known limitations")).toBeInTheDocument()
  })

  it("renders determinism explanation mentioning AAPL", () => {
    render(<TransparencySection />)
    expect(
      screen.getByText(/Enter AAPL today and tomorrow with the same data/)
    ).toBeInTheDocument()
  })
})

describe("CTASection", () => {
  it("renders CTA description", () => {
    render(<CTASection />)
    expect(
      screen.getByText(/See the full pipeline in action/)
    ).toBeInTheDocument()
  })

  it("renders CTA links with correct hrefs", () => {
    render(<CTASection />)
    const dashboardLink = screen.getByRole("link", {
      name: /Explore the Dashboard/i,
    })
    expect(dashboardLink).toHaveAttribute("href", "/dashboard")

    const guidesLink = screen.getByRole("link", {
      name: /Read the Guides/i,
    })
    expect(guidesLink).toHaveAttribute("href", "/guides")
  })
})
