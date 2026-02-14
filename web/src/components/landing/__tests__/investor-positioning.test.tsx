import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { InvestorPositioning } from "../investor-positioning"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

describe("InvestorPositioning", () => {
  it("renders the headline", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText("Discipline compounds.")).toBeInTheDocument()
  })

  it("renders the body text", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/same rigor to every decision/i)).toBeInTheDocument()
  })

  it("renders the data point", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/5–10 positions/i)).toBeInTheDocument()
  })

  it("renders the data caption", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/exceptional conviction/i)).toBeInTheDocument()
  })
})
