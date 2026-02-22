import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ActiveIncidents, IncidentHistory } from "../incident-list"
import type { Incident } from "../status-types"

const activeIncident: Incident = {
  id: "test-active",
  title: "API latency spike",
  status: "investigating",
  severity: "minor",
  createdAt: "2026-02-22T10:00:00Z",
  resolvedAt: null,
  updates: [
    { message: "Investigating increased latency.", timestamp: "2026-02-22T10:00:00Z" },
  ],
}

const resolvedIncident: Incident = {
  id: "test-resolved",
  title: "Scheduled maintenance",
  status: "resolved",
  severity: "maintenance",
  createdAt: "2026-02-20T02:00:00Z",
  resolvedAt: "2026-02-20T03:30:00Z",
  updates: [
    { message: "Maintenance complete.", timestamp: "2026-02-20T03:30:00Z" },
    { message: "Maintenance has begun.", timestamp: "2026-02-20T02:00:00Z" },
  ],
}

describe("ActiveIncidents", () => {
  it("renders active incident title", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("API latency spike")).toBeInTheDocument()
  })

  it("renders active incident heading", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("Active Incidents")).toBeInTheDocument()
  })

  it("renders the latest update message", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("Investigating increased latency.")).toBeInTheDocument()
  })

  it("renders status badge", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("investigating")).toBeInTheDocument()
  })

  it("renders nothing when no active incidents", () => {
    const { container } = render(<ActiveIncidents incidents={[]} />)
    expect(container.firstElementChild).toBeNull()
  })
})

describe("IncidentHistory", () => {
  it("renders resolved incident title", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    expect(screen.getByText("Scheduled maintenance")).toBeInTheDocument()
  })

  it("renders section heading", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    expect(screen.getByText("Past Incidents")).toBeInTheDocument()
  })

  it("shows empty message when no history", () => {
    render(<IncidentHistory incidents={[]} />)
    expect(screen.getByText("No incidents reported in the last 30 days.")).toBeInTheDocument()
  })

  it("renders resolved date", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    const matches = screen.getAllByText(/Feb/)
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })
})
