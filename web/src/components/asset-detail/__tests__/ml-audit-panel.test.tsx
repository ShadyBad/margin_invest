import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MLAuditPanel } from "../ml-audit-panel"

const nullProps = {
  mlModelQualified: null,
  mlModelRankIc: null,
  mlModelTrainedAt: null,
  mlAlpha: null,
  mlConfidence: null,
  mlOverride: null,
  rulesTier: null,
  compositeTier: null,
}

describe("MLAuditPanel", () => {
  it("renders nothing when no ML data at all", () => {
    const { container } = render(<MLAuditPanel {...nullProps} />)
    expect(container.firstChild).toBeEmptyDOMElement()
  })

  it("shows no-model state when ml_model_qualified is false", () => {
    render(
      <MLAuditPanel
        {...nullProps}
        mlModelQualified={false}
        mlModelRankIc={0.08}
        mlModelTrainedAt="2026-02-20T02:00:00Z"
      />
    )
    expect(screen.getByText("Machine Learning Audit")).toBeInTheDocument()
    expect(screen.getByText("No qualified model")).toBeInTheDocument()
    // Rank IC 0.08 appears in both the metric line and explanation
    expect(screen.getAllByText(/0\.08/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/rules-only/i)).toBeInTheDocument()
  })

  it("shows qualified-no-override state", () => {
    render(
      <MLAuditPanel
        {...nullProps}
        mlModelQualified={true}
        mlModelRankIc={0.23}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={3.2}
        mlConfidence={0.72}
        mlOverride="none"
        rulesTier="high"
        compositeTier="high"
      />
    )
    expect(screen.getByText("Machine Learning Audit")).toBeInTheDocument()
    expect(screen.getByText("Qualified")).toBeInTheDocument()
    expect(screen.getByText(/0\.23/)).toBeInTheDocument()
    expect(screen.getByText(/72%/)).toBeInTheDocument()
    expect(screen.getByText("None")).toBeInTheDocument()
    expect(
      screen.getByText(/ML signal did not meet override thresholds/)
    ).toBeInTheDocument()
  })

  it("shows promoted override state", () => {
    render(
      <MLAuditPanel
        {...nullProps}
        mlModelQualified={true}
        mlModelRankIc={0.25}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={5.1}
        mlConfidence={0.85}
        mlOverride="promoted"
        rulesTier="medium"
        compositeTier="high"
      />
    )
    expect(screen.getByText("PROMOTED")).toBeInTheDocument()
    expect(screen.getByText("Qualified")).toBeInTheDocument()
    expect(screen.getByText(/0\.25/)).toBeInTheDocument()
    expect(screen.getByText(/85%/)).toBeInTheDocument()
    // Tier transition: medium -> high
    expect(screen.getByText(/promoted from medium to high/i)).toBeInTheDocument()
  })

  it("shows demoted override state", () => {
    render(
      <MLAuditPanel
        {...nullProps}
        mlModelQualified={true}
        mlModelRankIc={0.21}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={-2.4}
        mlConfidence={0.78}
        mlOverride="demoted"
        rulesTier="high"
        compositeTier="medium"
      />
    )
    expect(screen.getByText("DEMOTED")).toBeInTheDocument()
    expect(screen.getByText("Qualified")).toBeInTheDocument()
    expect(screen.getByText(/78%/)).toBeInTheDocument()
  })
})
