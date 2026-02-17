import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AiSummary } from "../ai-summary"

vi.mock("../pro-gate", () => ({
  ProGate: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pro-gate">{children}</div>
  ),
}))

describe("AiSummary", () => {
  it("renders summary text and confidence bar", () => {
    render(
      <AiSummary summary="AAPL demonstrates strong quality." confidence={78} />
    )
    expect(screen.getByText("AAPL demonstrates strong quality.")).toBeInTheDocument()
    expect(screen.getByText("78")).toBeInTheDocument()
    expect(screen.getByText("AI ANALYSIS")).toBeInTheDocument()
  })

  it("renders confidence bar with correct width style", () => {
    render(<AiSummary summary="Test" confidence={65} />)
    const bar = screen.getByTestId("confidence-bar-fill")
    expect(bar.style.width).toBe("65%")
  })

  it("wraps in ProGate", () => {
    render(<AiSummary summary="Test" confidence={50} />)
    expect(screen.getByTestId("pro-gate")).toBeInTheDocument()
  })
})
