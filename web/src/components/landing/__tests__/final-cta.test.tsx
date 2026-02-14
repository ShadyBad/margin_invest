import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FinalCTA } from "../final-cta"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("FinalCTA", () => {
  it("renders the headline", () => {
    render(<FinalCTA />)
    expect(screen.getByText("See what survives the filter.")).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<FinalCTA />)
    const cta = screen.getByRole("link", { name: "Explore the Engine" })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary link", () => {
    render(<FinalCTA />)
    expect(screen.getByText(/read the methodology/i)).toBeInTheDocument()
  })

  it("contains the grid overlay", () => {
    const { container } = render(<FinalCTA />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })
})
