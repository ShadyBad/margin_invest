import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConsistencyBadge } from "../consistency-badge"

describe("ConsistencyBadge", () => {
  it("renders nothing when no warnings", () => {
    const { container } = render(<ConsistencyBadge warnings={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders warning badge when anomalies present", () => {
    const warnings = [
      {
        field_name: "shares_outstanding",
        z_score: 10.5,
        current_value: 4000000,
        historical_mean: 1000000,
      },
    ]
    render(<ConsistencyBadge warnings={warnings} />)
    expect(screen.getByText(/data anomaly/i)).toBeInTheDocument()
  })

  it("lists affected fields with human-readable labels", () => {
    const warnings = [
      {
        field_name: "shares_outstanding",
        z_score: 10.5,
        current_value: 4000000,
        historical_mean: 1000000,
      },
      {
        field_name: "revenue",
        z_score: -4.2,
        current_value: 20000,
        historical_mean: 100000,
      },
    ]
    render(<ConsistencyBadge warnings={warnings} />)
    expect(screen.getByText(/Shares Outstanding/)).toBeInTheDocument()
    expect(screen.getByText(/Revenue/)).toBeInTheDocument()
  })

  it("falls back to raw field_name when no label defined", () => {
    const warnings = [
      {
        field_name: "some_exotic_field",
        z_score: 5.0,
        current_value: 999,
        historical_mean: 100,
      },
    ]
    render(<ConsistencyBadge warnings={warnings} />)
    expect(screen.getByText(/some_exotic_field/)).toBeInTheDocument()
  })

  it("includes sigma deviation description", () => {
    const warnings = [
      {
        field_name: "total_assets",
        z_score: 3.5,
        current_value: 500,
        historical_mean: 100,
      },
    ]
    render(<ConsistencyBadge warnings={warnings} />)
    const badge = screen.getByTestId("consistency-badge")
    expect(badge.textContent).toContain("from history")
  })
})
