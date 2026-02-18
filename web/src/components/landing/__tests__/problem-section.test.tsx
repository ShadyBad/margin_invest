import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
  },
}))

import { ProblemSection } from "../problem-section"

describe("ProblemSection", () => {
  it("renders headline", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()
  })

  it("renders all four problems", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/filtering discipline/i)).toBeInTheDocument()
    expect(screen.getByText(/factor weighting/i)).toBeInTheDocument()
    expect(screen.getByText(/sector normalization/i)).toBeInTheDocument()
    expect(screen.getByText(/correlation awareness/i)).toBeInTheDocument()
  })

  it("renders closer line", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/replaces guesswork/i)).toBeInTheDocument()
  })
})
