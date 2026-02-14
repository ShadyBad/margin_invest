import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FrictionSection } from "../friction-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("FrictionSection", () => {
  it("renders the main headline", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/conviction they haven't earned/i)).toBeInTheDocument()
  })

  it("renders three friction points", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/emotion enters before analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/inconsistent frameworks/i)).toBeInTheDocument()
    expect(screen.getByText(/retail tools measure activity/i)).toBeInTheDocument()
  })

  it("uses asymmetric two-column layout", () => {
    const { container } = render(<FrictionSection />)
    const grid = container.querySelector("[class*='grid-cols-12']")
    expect(grid).toBeInTheDocument()
  })
})
