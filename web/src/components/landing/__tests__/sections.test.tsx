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
}))

import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "../sections"

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders the subline", () => {
    render(<HeroSection />)
    expect(screen.getByText("A deterministic scoring engine for capital allocation.")).toBeInTheDocument()
  })

  it("renders the primary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders the secondary link", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /view methodology/i })).toBeInTheDocument()
  })
})

describe("FrictionSection", () => {
  it("renders three declarative lines", () => {
    render(<FrictionSection />)
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    expect(screen.getByText("Few operate with structure.")).toBeInTheDocument()
    expect(screen.getByText("Emotion is expensive.")).toBeInTheDocument()
  })

  it("renders the behavioral finance citation", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/Barber & Odean/)).toBeInTheDocument()
  })
})

describe("EngineDiagram", () => {
  it("renders four diagram node labels", () => {
    render(<EngineDiagram />)
    expect(screen.getAllByText("Market Data").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Risk Modeling").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Allocation Engine").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Decision Clarity").length).toBeGreaterThanOrEqual(1)
  })

  it("renders the section label", () => {
    render(<EngineDiagram />)
    expect(screen.getByText(/how the engine works/i)).toBeInTheDocument()
  })
})

describe("EngineProof", () => {
  it("renders the heading and dashboard panels", () => {
    render(<EngineProof />)
    expect(screen.getByText("What the engine produces.")).toBeInTheDocument()
    expect(screen.getAllByText(/Composite Score/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Risk Breakdown/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Factor Weights/i).length).toBeGreaterThanOrEqual(1)
  })
})

describe("CapabilitiesSection", () => {
  it("renders four capability titles", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    expect(screen.getByText("Quantified Risk")).toBeInTheDocument()
    expect(screen.getByText("Scenario Modeling")).toBeInTheDocument()
    expect(screen.getByText("Bias Reduction")).toBeInTheDocument()
  })
})

describe("InvestorPositioning", () => {
  it("renders the headline", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/not trading/i)).toBeInTheDocument()
  })
})

describe("FinalCTA", () => {
  it("renders the CTA heading and button", () => {
    render(<FinalCTA />)
    expect(screen.getByText("Start with structure.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders the updated CTA subtext", () => {
    render(<FinalCTA />)
    expect(screen.getByText("Run any equity through the engine.")).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<FinalCTA />)
    expect(screen.getByRole("link", { name: /methodology/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
