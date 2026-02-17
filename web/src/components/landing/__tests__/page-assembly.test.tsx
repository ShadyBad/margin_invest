// web/src/components/landing/__tests__/page-assembly.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock next/dynamic to render nothing for WebGL components
vi.mock("next/dynamic", () => ({
  default: () => {
    const MockComponent = () => null
    MockComponent.displayName = "DynamicMock"
    return MockComponent
  },
}))

// Mock next-themes for NavMinimal
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "dark", setTheme: vi.fn() }),
}))

// Mock framer-motion to avoid IntersectionObserver issues in jsdom
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

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all 7 sections", () => {
    render(<Page />)
    // Hero
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
    // Friction
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    // Engine Diagram - use getAllByText since desktop+mobile both render
    expect(screen.getAllByText("Market Data").length).toBeGreaterThan(0)
    // Engine Proof
    expect(screen.getByText("What the engine produces.")).toBeInTheDocument()
    // Capabilities
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    // Investor Positioning
    expect(screen.getByText(/not trading/i)).toBeInTheDocument()
    // Final CTA
    const ctaLinks = screen.getAllByRole("link", { name: /explore the engine/i })
    expect(ctaLinks.length).toBeGreaterThanOrEqual(2) // hero + final CTA at minimum
  })

  it("renders the minimal nav with Dashboard link", () => {
    render(<Page />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
    const dashboardLinks = screen.getAllByRole("link", { name: /^dashboard$/i })
    expect(dashboardLinks.length).toBeGreaterThanOrEqual(1)
  })
})
