import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { InsightPanel } from "../insight-panel"

describe("InsightPanel", () => {
  const baseProps = {
    strengths: ["Exceptional value — top 2% on FCF yield", "Strong momentum"],
    risks: ["Liquidity filter failed", "Insufficient Beneish M-Score data"],
    commentary: "TISNF presents a compelling value opportunity with exceptional momentum.",
    confidence: 78,
  }

  it("renders strengths card with items", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Strengths")).toBeInTheDocument()
    expect(screen.getByText("Exceptional value — top 2% on FCF yield")).toBeInTheDocument()
    expect(screen.getByText("Strong momentum")).toBeInTheDocument()
  })

  it("renders risk flags card", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Risk Flags")).toBeInTheDocument()
    expect(screen.getByText("Liquidity filter failed")).toBeInTheDocument()
  })

  it("renders commentary card", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Analysis")).toBeInTheDocument()
    expect(screen.getByText(baseProps.commentary)).toBeInTheDocument()
  })

  it("renders confidence bar with percentage", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("AI Confidence")).toBeInTheDocument()
    expect(screen.getByText("78%")).toBeInTheDocument()
  })

  it("renders empty strengths gracefully", () => {
    render(<InsightPanel {...baseProps} strengths={[]} />)
    expect(screen.getByText("Strengths")).toBeInTheDocument()
  })
})
