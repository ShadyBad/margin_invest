import { describe, it, expect } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { DeterminismBadge } from "../determinism-badge"

describe("DeterminismBadge", () => {
  it("renders the determinism statement", () => {
    render(<DeterminismBadge />)
    const badge = screen.getByTestId("determinism-badge")
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent("Deterministic")
    expect(badge).toHaveTextContent("same inputs produce this exact output")
  })

  it("shows tooltip on hover", async () => {
    render(<DeterminismBadge />)
    const badge = screen.getByTestId("determinism-badge")
    fireEvent.mouseEnter(badge)

    await waitFor(() => {
      expect(screen.getByText(/zero human intervention/)).toBeInTheDocument()
    })
  })

  it("hides tooltip on mouse leave", async () => {
    render(<DeterminismBadge />)
    const badge = screen.getByTestId("determinism-badge")

    fireEvent.mouseEnter(badge)
    await waitFor(() => {
      expect(screen.getByText(/zero human intervention/)).toBeInTheDocument()
    })

    fireEvent.mouseLeave(badge)
    await waitFor(() => {
      expect(screen.queryByText(/zero human intervention/)).not.toBeInTheDocument()
    })
  })
})
