import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ServiceCards } from "../service-cards"
import type { ServiceInfo } from "../status-types"

const mockServices: ServiceInfo[] = [
  { name: "API", status: "operational", description: "Platform availability" },
  { name: "Database", status: "outage", description: "Data storage" },
  { name: "Scoring Engine", status: "unknown", description: "Score computation" },
]

describe("ServiceCards", () => {
  it("renders all service names", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Database")).toBeInTheDocument()
    expect(screen.getByText("Scoring Engine")).toBeInTheDocument()
  })

  it("renders all service descriptions", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("Platform availability")).toBeInTheDocument()
    expect(screen.getByText("Data storage")).toBeInTheDocument()
    expect(screen.getByText("Score computation")).toBeInTheDocument()
  })

  it("renders status labels", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("Operational")).toBeInTheDocument()
    expect(screen.getByText("Outage")).toBeInTheDocument()
    expect(screen.getByText("Unknown")).toBeInTheDocument()
  })

  it("applies green dot for operational", () => {
    const { container } = render(
      <ServiceCards services={[{ name: "API", status: "operational", description: "Test" }]} />
    )
    const dot = container.querySelector("[data-status='operational']")
    expect(dot).toBeInTheDocument()
  })

  it("applies red dot for outage", () => {
    const { container } = render(
      <ServiceCards services={[{ name: "API", status: "outage", description: "Test" }]} />
    )
    const dot = container.querySelector("[data-status='outage']")
    expect(dot).toBeInTheDocument()
  })
})
