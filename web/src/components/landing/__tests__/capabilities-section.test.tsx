import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { CapabilitiesSection } from "../capabilities-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("CapabilitiesSection", () => {
  it("renders four capability headlines", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText(/sector-neutral ranking/i)).toBeInTheDocument()
    expect(screen.getByText(/growth stage calibrates/i)).toBeInTheDocument()
    expect(screen.getByText(/elimination runs before/i)).toBeInTheDocument()
    expect(screen.getByText(/determinism means/i)).toBeInTheDocument()
  })

  it("renders capability descriptions", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText(/GICS sector first/i)).toBeInTheDocument()
    expect(screen.getByText(/reproducible/i)).toBeInTheDocument()
  })
})
