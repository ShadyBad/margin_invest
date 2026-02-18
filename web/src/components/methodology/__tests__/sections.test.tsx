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
  ProblemSection,
  ApproachSection,
  EngineSection,
  OutputsSection,
  WhySection,
  TrustSection,
  MethodologyCTA,
} from "../index"

describe("ProblemSection", () => {
  it("renders the headline", () => {
    render(<ProblemSection />)
    expect(
      screen.getByText("Most investment research creates noise, not clarity.")
    ).toBeInTheDocument()
  })

  it("renders all four pain points", () => {
    render(<ProblemSection />)
    expect(screen.getByText("Noisy markets")).toBeInTheDocument()
    expect(screen.getByText("Information overload")).toBeInTheDocument()
    expect(screen.getByText("Emotional decision-making")).toBeInTheDocument()
    expect(screen.getByText("No repeatable process")).toBeInTheDocument()
  })
})

describe("ApproachSection", () => {
  it("renders the headline", () => {
    render(<ApproachSection />)
    expect(
      screen.getByText(
        "A systematic engine for asymmetric opportunities."
      )
    ).toBeInTheDocument()
  })
})

describe("EngineSection", () => {
  it("renders the section label and headline", () => {
    render(<EngineSection />)
    expect(screen.getByText("The Engine")).toBeInTheDocument()
    expect(
      screen.getByText("From raw data to conviction.")
    ).toBeInTheDocument()
  })

  it("renders three factor pillars", () => {
    render(<EngineSection />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })
})

describe("OutputsSection", () => {
  it("renders the headline", () => {
    render(<OutputsSection />)
    expect(
      screen.getByText("Structured outputs, not opinions.")
    ).toBeInTheDocument()
  })

  it("renders all four output cards", () => {
    render(<OutputsSection />)
    expect(screen.getByText("Candidate cards")).toBeInTheDocument()
    expect(screen.getByText("Factor breakdown")).toBeInTheDocument()
    expect(screen.getByText("Price target framework")).toBeInTheDocument()
    expect(screen.getByText("Allocation guidance")).toBeInTheDocument()
  })
})

describe("WhySection", () => {
  it("renders the headline", () => {
    render(<WhySection />)
    expect(screen.getByText("Why this exists.")).toBeInTheDocument()
  })

  it("renders the comparison table", () => {
    render(<WhySection />)
    expect(screen.getByText("Capability")).toBeInTheDocument()
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })
})

describe("TrustSection", () => {
  it("renders the headline", () => {
    render(<TrustSection />)
    expect(
      screen.getByText(/What this is — and isn't./)
    ).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TrustSection />)
    expect(screen.getByText("Not financial advice")).toBeInTheDocument()
    expect(screen.getByText("Model risk exists")).toBeInTheDocument()
    expect(screen.getByText("Structure, not prediction")).toBeInTheDocument()
  })
})

describe("MethodologyCTA", () => {
  it("renders the CTA heading and buttons", () => {
    render(<MethodologyCTA />)
    expect(
      screen.getByText("Start building a disciplined watchlist.")
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /see your dashboard/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /learn about pricing/i })
    ).toBeInTheDocument()
  })
})
