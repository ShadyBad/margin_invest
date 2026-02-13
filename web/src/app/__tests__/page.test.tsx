import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import Page from "../page"

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, initial, animate, whileInView, viewport, transition, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, initial, animate, whileInView, viewport, transition, ...props }: any) => <h2 {...props}>{children}</h2>,
  },
}))

describe("Landing Page", () => {
  it("renders hero section with headline", () => {
    render(<Page />)
    expect(screen.getByText(/once-in-a-generation/i)).toBeInTheDocument()
  })

  it("renders Get Started CTA", () => {
    render(<Page />)
    expect(screen.getByText("Get Started")).toBeInTheDocument()
  })

  it("renders How It Works section", () => {
    render(<Page />)
    expect(screen.getByText("How It Works")).toBeInTheDocument()
  })

  it("renders Performance section", () => {
    render(<Page />)
    expect(screen.getByText("Performance")).toBeInTheDocument()
  })
})
