import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import Page from "../page"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    rect: (props: any) => <rect {...props} />,
    text: ({ children, ...props }: any) => <text {...props}>{children}</text>,
    line: (props: any) => <line {...props} />,
    path: (props: any) => <path {...props} />,
    g: ({ children, ...props }: any) => <g {...props}>{children}</g>,
  },
  useInView: () => true,
}))

describe("Landing Page", () => {
  it("renders hero section with headline", () => {
    render(<Page />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders primary CTA", () => {
    render(<Page />)
    const ctas = screen.getAllByText("Explore the Engine")
    expect(ctas.length).toBeGreaterThanOrEqual(1)
  })

  it("renders friction section", () => {
    render(<Page />)
    expect(screen.getByText(/conviction they haven't earned/i)).toBeInTheDocument()
  })

  it("renders system diagram section", () => {
    render(<Page />)
    expect(screen.getByText("How the engine works")).toBeInTheDocument()
  })

  it("renders engine proof section", () => {
    render(<Page />)
    expect(screen.getByText("What the output looks like")).toBeInTheDocument()
  })

  it("renders capabilities section", () => {
    render(<Page />)
    expect(screen.getByText(/sector-neutral ranking/i)).toBeInTheDocument()
  })

  it("renders investor positioning section", () => {
    render(<Page />)
    expect(screen.getByText("Discipline compounds.")).toBeInTheDocument()
  })

  it("renders final CTA section", () => {
    render(<Page />)
    expect(screen.getByText("See what survives the filter.")).toBeInTheDocument()
  })
})
