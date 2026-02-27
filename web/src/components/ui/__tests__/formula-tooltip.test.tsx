import { describe, it, expect } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { FormulaTooltip } from "../formula-tooltip"
import { FORMULA_DEFINITIONS } from "@/lib/formula-definitions"

describe("FormulaTooltip", () => {
  it("renders trigger with info icon for known metric", () => {
    render(
      <FormulaTooltip metricKey="altman_z_score">
        <span>Z-Score</span>
      </FormulaTooltip>
    )
    const trigger = screen.getByTestId("formula-trigger-altman_z_score")
    expect(trigger).toBeInTheDocument()
    // Info icon SVG should be present
    const svg = trigger.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })

  it("shows tooltip content on mouseEnter", async () => {
    render(
      <FormulaTooltip metricKey="altman_z_score">
        <span>Z-Score</span>
      </FormulaTooltip>
    )
    const trigger = screen.getByTestId("formula-trigger-altman_z_score")
    fireEvent.mouseEnter(trigger)

    await waitFor(() => {
      expect(screen.getByRole("tooltip")).toBeInTheDocument()
    })

    // Check all four content lines
    expect(screen.getByText("Altman Z-Score")).toBeInTheDocument()
    expect(screen.getByText(FORMULA_DEFINITIONS.altman_z_score.formula)).toBeInTheDocument()
    expect(screen.getByText("Altman (1968)")).toBeInTheDocument()
    expect(
      screen.getByText("Below 1.81 = distress zone. Above 2.99 = safe zone.")
    ).toBeInTheDocument()
  })

  it("hides tooltip content on mouseLeave", async () => {
    render(
      <FormulaTooltip metricKey="altman_z_score">
        <span>Z-Score</span>
      </FormulaTooltip>
    )
    const trigger = screen.getByTestId("formula-trigger-altman_z_score")

    fireEvent.mouseEnter(trigger)
    await waitFor(() => {
      expect(screen.getByRole("tooltip")).toBeInTheDocument()
    })

    fireEvent.mouseLeave(trigger)
    await waitFor(() => {
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument()
    })
  })

  it("renders children only for unknown metricKey (no trigger, no icon)", () => {
    render(
      <FormulaTooltip metricKey="totally_unknown_metric">
        <span>Some Label</span>
      </FormulaTooltip>
    )
    expect(screen.getByText("Some Label")).toBeInTheDocument()
    expect(screen.queryByTestId("formula-trigger-totally_unknown_metric")).not.toBeInTheDocument()
  })

  it("every key in FORMULA_DEFINITIONS has all required fields", () => {
    const keys = Object.keys(FORMULA_DEFINITIONS)
    expect(keys.length).toBeGreaterThan(0)

    for (const key of keys) {
      const def = FORMULA_DEFINITIONS[key]
      expect(def.name, `${key}.name`).toBeTruthy()
      expect(def.formula, `${key}.formula`).toBeTruthy()
      expect(def.source, `${key}.source`).toBeTruthy()
      expect(def.interpretation, `${key}.interpretation`).toBeTruthy()
    }
  })
})
