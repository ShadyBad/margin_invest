import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { EngineProof } from "../engine-proof"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

describe("EngineProof", () => {
  it("renders section label", () => {
    render(<EngineProof />)
    expect(screen.getByText("What the output looks like")).toBeInTheDocument()
  })

  it("renders factor breakdown panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })

  it("renders conviction badge panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Exceptional")).toBeInTheDocument()
  })

  it("renders filter results panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Beneish M-Score")).toBeInTheDocument()
  })

  it("renders caption", () => {
    render(<EngineProof />)
    expect(screen.getByText(/same inputs, same outputs/i)).toBeInTheDocument()
  })
})
