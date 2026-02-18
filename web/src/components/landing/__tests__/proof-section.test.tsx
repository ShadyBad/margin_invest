import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  useInView: () => true,
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()
  })

  it("renders all 4 proof cards", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText(/factor transparency/i)).toBeInTheDocument()
    expect(screen.getByText(/growth vs value/i)).toBeInTheDocument()
    expect(screen.getByText(/portfolio view/i)).toBeInTheDocument()
    expect(screen.getByText(/historical application/i)).toBeInTheDocument()
  })

  it("renders factor percentile bars", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })
})
