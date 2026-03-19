import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { PipelineStatus } from "../pipeline-status"

const mockDashboard = {
  pending_count: 3,
  avg_approval_latency_hours: 2.5,
  rejection_rate: 0.123,
  recent_anomalies: [],
}

const mockTransparency = {
  oversight_levels: {},
  last_approvals: {},
  pipeline_health: {
    status: "idle",
    last_successful_run: "2026-02-27T08:30:00Z",
  },
}

vi.mock("@/lib/api/governance", () => ({
  getDashboard: vi.fn(),
  getTransparency: vi.fn(),
}))

import { getDashboard, getTransparency } from "@/lib/api/governance"

const mockedGetDashboard = vi.mocked(getDashboard)
const mockedGetTransparency = vi.mocked(getTransparency)

beforeEach(() => {
  vi.clearAllMocks()
  mockedGetDashboard.mockResolvedValue(mockDashboard)
  mockedGetTransparency.mockResolvedValue(mockTransparency)
})

describe("PipelineStatus", () => {
  it("renders pending count", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument()
    })
    expect(screen.getByText("Pending Approvals")).toBeInTheDocument()
  })

  it("renders pending count with warning color when > 0", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-pending-value")).toBeInTheDocument()
    })
    const value = screen.getByTestId("stat-pending-value")
    expect(value).toHaveTextContent("3")
    expect(value.className).toContain("text-warning")
  })

  it("renders pending count without warning color when 0", async () => {
    mockedGetDashboard.mockResolvedValue({ ...mockDashboard, pending_count: 0 })
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-pending-value")).toBeInTheDocument()
    })
    const value = screen.getByTestId("stat-pending-value")
    expect(value).toHaveTextContent("0")
    expect(value.className).not.toContain("text-warning")
  })

  it("renders avg latency", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("2.5 hours")).toBeInTheDocument()
    })
    expect(screen.getByText("Avg Approval Latency")).toBeInTheDocument()
  })

  it("renders rejection rate as percentage", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("12.3%")).toBeInTheDocument()
    })
    expect(screen.getByText("Rejection Rate")).toBeInTheDocument()
  })

  it('shows "\u2014" for null avg latency', async () => {
    mockedGetDashboard.mockResolvedValue({
      ...mockDashboard,
      avg_approval_latency_hours: null,
    })
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-latency-value")).toBeInTheDocument()
    })
    expect(screen.getByTestId("stat-latency-value")).toHaveTextContent("\u2014")
  })

  it('shows "\u2014" for null rejection rate', async () => {
    mockedGetDashboard.mockResolvedValue({
      ...mockDashboard,
      rejection_rate: null,
    })
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-rejection-value")).toBeInTheDocument()
    })
    expect(screen.getByTestId("stat-rejection-value")).toHaveTextContent("\u2014")
  })

  it("renders pipeline status", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("idle")).toBeInTheDocument()
    })
    expect(screen.getByText("Pipeline Status")).toBeInTheDocument()
  })

  it("renders pipeline status as running", async () => {
    mockedGetTransparency.mockResolvedValue({
      ...mockTransparency,
      pipeline_health: { status: "running", last_successful_run: null },
    })
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("running")).toBeInTheDocument()
    })
  })

  it("renders last successful run datetime", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByText("Last Successful Run")).toBeInTheDocument()
    })
    // Should display a formatted datetime
    expect(screen.getByTestId("stat-last-run-value")).not.toHaveTextContent("\u2014")
  })

  it('shows "\u2014" for null last successful run', async () => {
    mockedGetTransparency.mockResolvedValue({
      ...mockTransparency,
      pipeline_health: { status: "idle", last_successful_run: null },
    })
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("stat-last-run-value")).toBeInTheDocument()
    })
    expect(screen.getByTestId("stat-last-run-value")).toHaveTextContent("\u2014")
  })

  it("calls getDashboard without arguments", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(mockedGetDashboard).toHaveBeenCalledWith()
    })
  })

  it("calls getTransparency without arguments", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(mockedGetTransparency).toHaveBeenCalledWith()
    })
  })

  it("uses terminal-card class on the container", async () => {
    render(<PipelineStatus />)
    await waitFor(() => {
      expect(screen.getByTestId("pipeline-status")).toBeInTheDocument()
    })
    expect(screen.getByTestId("pipeline-status").className).toContain("terminal-card")
  })

  it("shows loading state initially", () => {
    // Never resolve the promises
    mockedGetDashboard.mockReturnValue(new Promise(() => {}))
    mockedGetTransparency.mockReturnValue(new Promise(() => {}))
    render(<PipelineStatus />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})
