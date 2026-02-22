import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StatusPageClient } from "../status-page-client"
import type { StatusResponse } from "../status-types"

const operationalResponse: StatusResponse = {
  status: "operational",
  services: { api: "operational", database: "operational", scoring: "operational" },
  version: "0.1.0",
  incidents: [],
}

const degradedResponse: StatusResponse = {
  status: "degraded",
  services: { api: "operational", database: "operational", scoring: "outage" },
  version: "0.1.0",
  incidents: [
    {
      id: "test-1",
      title: "Scoring delays",
      status: "investigating",
      severity: "minor",
      createdAt: "2026-02-22T10:00:00Z",
      resolvedAt: null,
      updates: [{ message: "Looking into it.", timestamp: "2026-02-22T10:00:00Z" }],
    },
  ],
}

const withHistoryResponse: StatusResponse = {
  status: "operational",
  services: { api: "operational", database: "operational", scoring: "operational" },
  version: "0.1.0",
  incidents: [
    {
      id: "past-1",
      title: "Past maintenance",
      status: "resolved",
      severity: "maintenance",
      createdAt: "2026-02-20T02:00:00Z",
      resolvedAt: "2026-02-20T03:00:00Z",
      updates: [{ message: "Done.", timestamp: "2026-02-20T03:00:00Z" }],
    },
  ],
}

describe("StatusPageClient integration", () => {
  it("renders operational state correctly", () => {
    render(<StatusPageClient initial={operationalResponse} />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Database")).toBeInTheDocument()
    expect(screen.getByText("Scoring Engine")).toBeInTheDocument()
    expect(screen.getByText("No incidents reported in the last 30 days.")).toBeInTheDocument()
  })

  it("renders degraded state with active incident", () => {
    render(<StatusPageClient initial={degradedResponse} />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
    expect(screen.getByText("Scoring delays")).toBeInTheDocument()
    expect(screen.getByText("Looking into it.")).toBeInTheDocument()
  })

  it("renders incident history", () => {
    render(<StatusPageClient initial={withHistoryResponse} />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
    expect(screen.getByText("Past maintenance")).toBeInTheDocument()
  })

  it("renders fallback when initial is null", () => {
    render(<StatusPageClient initial={null} />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
    expect(screen.getByText(/Unable to load status information/)).toBeInTheDocument()
  })

  it("shows last updated timestamp", () => {
    render(<StatusPageClient initial={operationalResponse} />)
    expect(screen.getByText(/Last updated/)).toBeInTheDocument()
    expect(screen.getByText(/Refreshes every 30 seconds/)).toBeInTheDocument()
  })
})
