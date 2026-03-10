import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreHeader } from "../score-header"

describe("ScoreHeader", () => {
  it("renders score and tier", () => {
    render(<ScoreHeader score={85} tier="strong" percentile={92} />)
    expect(screen.getByText("85")).toBeInTheDocument()
  })

  it("renders tier badge with tier name", () => {
    render(<ScoreHeader score={78} tier="high" percentile={88} />)
    const badge = screen.getByTestId("tier-badge")
    expect(badge).toHaveTextContent("high")
  })

  it("renders percentile value", () => {
    render(<ScoreHeader score={65} tier="medium" percentile={72} />)
    expect(screen.getByTestId("percentile-value")).toHaveTextContent("72th")
  })

  it("renders percentile bar fill with correct width", () => {
    render(<ScoreHeader score={90} tier="exceptional" percentile={95} />)
    const fill = screen.getByTestId("percentile-fill")
    expect(fill).toHaveStyle({ width: "95%" })
  })

  it("clamps percentile to 0-100 range", () => {
    render(<ScoreHeader score={10} tier="none" percentile={150} />)
    const fill = screen.getByTestId("percentile-fill")
    expect(fill).toHaveStyle({ width: "100%" })
  })

  it("rounds score to integer", () => {
    render(<ScoreHeader score={78.7} tier="high" percentile={88} />)
    expect(screen.getByTestId("score-value")).toHaveTextContent("79")
  })

  it("uses default style for unknown tier", () => {
    render(<ScoreHeader score={50} tier="unknown_tier" percentile={50} />)
    const badge = screen.getByTestId("tier-badge")
    expect(badge).toHaveTextContent("unknown_tier")
  })

  it("has testid on root element", () => {
    render(<ScoreHeader score={85} tier="high" percentile={92} />)
    expect(screen.getByTestId("score-header")).toBeInTheDocument()
  })
})
