import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StatusBanner } from "../status-banner"

describe("StatusBanner", () => {
  it("shows All Systems Operational for operational status", () => {
    render(<StatusBanner status="operational" />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
  })

  it("shows Partial Degradation for degraded status", () => {
    render(<StatusBanner status="degraded" />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
  })

  it("shows Major Outage for outage status", () => {
    render(<StatusBanner status="outage" />)
    expect(screen.getByText("Major Outage")).toBeInTheDocument()
  })

  it("applies green styling for operational", () => {
    const { container } = render(<StatusBanner status="operational" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-green")
  })

  it("applies amber styling for degraded", () => {
    const { container } = render(<StatusBanner status="degraded" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-amber")
  })

  it("applies red styling for outage", () => {
    const { container } = render(<StatusBanner status="outage" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-red")
  })
})
