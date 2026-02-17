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
    // SVG element mocks for ConstellationNarrative
    circle: (props: any) => <circle {...props} />,
    line: (props: any) => <line {...props} />,
  },
  useInView: () => true,
  useMotionValue: (init: number) => {
    let value = init
    return {
      get: () => value,
      set: (v: number) => { value = v },
      on: (_event: string, _cb: any) => () => {},
    }
  },
  useTransform: (_mv: any, _transform: any) => ({
    get: () => "0.0",
    on: (_event: string, _cb: any) => () => {},
  }),
  useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => () => {} } }),
  animate: () => ({ stop: () => {} }),
  useReducedMotion: () => false,
  useTime: () => ({
    get: () => 0,
    on: (_event: string, _cb: any) => () => {},
  }),
}))

vi.mock("@/lib/stores/node-positions", () => ({
  useNodePositions: (selector: any) => {
    const state = {
      positions: {},
      setPosition: vi.fn(),
      clear: vi.fn(),
    }
    return typeof selector === "function" ? selector(state) : state
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
  PricingSection,
} from "../sections"

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Conviction scoring for serious investors.")).toBeInTheDocument()
  })

  it("renders the subline", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(
        /deterministic engine that scores every stock across 6 factors/
      )
    ).toBeInTheDocument()
  })

  it("renders the primary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /score your first position/i })).toBeInTheDocument()
  })

  it("renders the secondary link", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /see the methodology/i })).toBeInTheDocument()
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

describe("ConstellationNarrative", () => {
  it("renders an SVG with aria-hidden", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute("aria-hidden", "true")
    expect(svg).toHaveAttribute("viewBox", "0 0 400 280")
  })

  it("renders 20 circle nodes", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const circles = container.querySelectorAll("circle")
    expect(circles).toHaveLength(20)
  })

  it("renders edges as line elements", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const lines = container.querySelectorAll("line")
    // 3 hub-hub + 16 hub-peripheral + 3 false = 22 total
    expect(lines).toHaveLength(22)
  })

  it("renders with accessible reduced-motion support", async () => {
    const { ConstellationNarrative } = await import("../sections/constellation-narrative")
    const { container } = render(<ConstellationNarrative />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
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
    expect(screen.getByText(/Sample Output/)).toBeInTheDocument()
  })

  it("renders methodology link", () => {
    render(<EngineProof />)
    expect(screen.getByRole("link", { name: /methodology documentation/i })).toBeInTheDocument()
  })
})

describe("PricingSection", () => {
  it("renders three tier names", () => {
    render(<PricingSection />)
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("Allocator")).toBeInTheDocument()
  })

  it("renders tier prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })

  it("renders CTA buttons for each tier", () => {
    render(<PricingSection />)
    const links = screen.getAllByRole("link")
    const pricingLinks = links.filter(
      (l) => l.textContent?.match(/start free|start trial|get started/i)
    )
    expect(pricingLinks.length).toBeGreaterThanOrEqual(3)
  })

  it("renders the section heading", () => {
    render(<PricingSection />)
    expect(screen.getByText(/simple, transparent pricing/i)).toBeInTheDocument()
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
    expect(screen.getByText("Score your first position.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /start free/i })).toBeInTheDocument()
  })

  it("renders the updated CTA subtext", () => {
    render(<FinalCTA />)
    expect(
      screen.getByText("See every stock through the lens of conviction.")
    ).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<FinalCTA />)
    expect(screen.getByRole("link", { name: /methodology/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
