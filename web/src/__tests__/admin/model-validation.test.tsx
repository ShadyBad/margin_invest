import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { SeedDistributionTable } from "@/components/admin/SeedDistributionTable"
import { SeedBoxPlot } from "@/components/admin/SeedBoxPlot"
import { SeedDetailTable } from "@/components/admin/SeedDetailTable"
import { ValidationChecklist } from "@/components/admin/ValidationChecklist"
import type {
  MetricDistribution,
  GateCheck,
  SeedDetail,
} from "@/lib/api/model-validation"

// Mock recharts for SeedBoxPlot tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children: React.ReactNode }) => <g>{children}</g>,
  Cell: () => null,
  XAxis: ({ label }: { label?: { value?: string } }) => (
    <div data-testid="x-axis">{label?.value}</div>
  ),
  YAxis: ({ label }: { label?: { value?: string } }) => (
    <div data-testid="y-axis">{label?.value}</div>
  ),
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
}))

// --- Test data ---

const mockDistributions: Record<string, MetricDistribution> = {
  rank_ic: {
    mean: 0.2345,
    median: 0.2301,
    std: 0.0123,
    min: 0.2,
    max: 0.28,
    ci_lower: 0.21,
    ci_upper: 0.26,
    cv: 0.05,
  },
  cluster_stability_ari: {
    mean: 0.85,
    median: 0.86,
    std: 0.03,
    min: 0.78,
    max: 0.91,
    ci_lower: 0.8,
    ci_upper: 0.9,
    cv: 0.04,
  },
}

const mockGateChecks: GateCheck[] = [
  { name: "median_rank_ic", value: 0.23, threshold: 0.15, passed: true },
  { name: "cv_rank_ic", value: 0.12, threshold: 0.3, passed: true },
  { name: "min_clusters", value: 2, threshold: 3, passed: false },
]

const mockSeedDetails: SeedDetail[] = [
  { seed: 42, rank_ic: 0.25, n_clusters: 4, n_samples: 150, selected: true },
  { seed: 7, rank_ic: 0.22, n_clusters: 3, n_samples: 150, selected: false },
  { seed: 99, rank_ic: 0.18, n_clusters: 5, n_samples: 150, selected: false },
]

// --- SeedDistributionTable tests ---

describe("SeedDistributionTable", () => {
  it("renders metric names", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    expect(screen.getByText("Rank Ic")).toBeInTheDocument()
    expect(screen.getByText("Cluster Stability Ari")).toBeInTheDocument()
  })

  it("renders mean value for rank_ic", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    const row = screen.getByTestId("dist-row-rank_ic")
    expect(row).toHaveTextContent("0.2345")
  })

  it("renders CI in bracket format", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    const row = screen.getByTestId("dist-row-rank_ic")
    expect(row).toHaveTextContent("[0.210, 0.260]")
  })

  it("renders CV value", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    const row = screen.getByTestId("dist-row-rank_ic")
    expect(row).toHaveTextContent("0.05")
  })

  it("uses terminal-card class", () => {
    render(<SeedDistributionTable distributions={mockDistributions} />)
    const container = screen.getByTestId("seed-distribution-table")
    expect(container.className).toContain("terminal-card")
  })

  it("renders empty state when no distributions", () => {
    render(<SeedDistributionTable distributions={{}} />)
    expect(screen.getByText("No distribution data available.")).toBeInTheDocument()
  })
})

// --- SeedBoxPlot tests ---

describe("SeedBoxPlot", () => {
  it("renders without crashing", () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    expect(screen.getByTestId("seed-box-plot")).toBeInTheDocument()
  })

  it('shows "Rank IC" y-axis label', () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    expect(screen.getByTestId("y-axis")).toHaveTextContent("Rank IC")
  })

  it('shows "Seed" x-axis label', () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    expect(screen.getByTestId("x-axis")).toHaveTextContent("Seed")
  })

  it("renders the bar chart", () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
  })

  it("uses terminal-card class", () => {
    render(<SeedBoxPlot seedDetails={mockSeedDetails} threshold={0.15} />)
    const container = screen.getByTestId("seed-box-plot")
    expect(container.className).toContain("terminal-card")
  })
})

// --- SeedDetailTable tests ---

describe("SeedDetailTable", () => {
  it("renders seed rows", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    expect(screen.getByText("Seed 7")).toBeInTheDocument()
    expect(screen.getByText("Seed 42")).toBeInTheDocument()
    expect(screen.getByText("Seed 99")).toBeInTheDocument()
  })

  it("sorts seeds by number", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    const rows = screen.getAllByTestId(/^seed-row-/)
    expect(rows[0]).toHaveAttribute("data-testid", "seed-row-7")
    expect(rows[1]).toHaveAttribute("data-testid", "seed-row-42")
    expect(rows[2]).toHaveAttribute("data-testid", "seed-row-99")
  })

  it("highlights selected seed with badge", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    expect(screen.getByTestId("selected-badge-42")).toBeInTheDocument()
    expect(screen.getByTestId("selected-badge-42")).toHaveTextContent("Selected")
  })

  it("does not show selected badge for non-selected seeds", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    expect(screen.queryByTestId("selected-badge-7")).not.toBeInTheDocument()
    expect(screen.queryByTestId("selected-badge-99")).not.toBeInTheDocument()
  })

  it("renders rank IC values", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    const row = screen.getByTestId("seed-row-42")
    expect(row).toHaveTextContent("0.2500")
  })

  it("renders cluster and sample counts", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    const row = screen.getByTestId("seed-row-42")
    expect(row).toHaveTextContent("4")
    expect(row).toHaveTextContent("150")
  })

  it("uses terminal-card class", () => {
    render(<SeedDetailTable details={mockSeedDetails} />)
    const container = screen.getByTestId("seed-detail-table")
    expect(container.className).toContain("terminal-card")
  })

  it("renders empty state when no details", () => {
    render(<SeedDetailTable details={[]} />)
    expect(screen.getByText("No seed details available.")).toBeInTheDocument()
  })
})

// --- ValidationChecklist tests ---

describe("ValidationChecklist", () => {
  it("renders gate checks", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={false} />)
    expect(screen.getByTestId("gate-check-median_rank_ic")).toBeInTheDocument()
    expect(screen.getByTestId("gate-check-cv_rank_ic")).toBeInTheDocument()
    expect(screen.getByTestId("gate-check-min_clusters")).toBeInTheDocument()
  })

  it("shows GATE PASSED when gatePassed is true", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    expect(screen.getByTestId("gate-status")).toHaveTextContent("GATE PASSED")
  })

  it("shows GATE FAILED when gatePassed is false", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={false} />)
    expect(screen.getByTestId("gate-status")).toHaveTextContent("GATE FAILED")
  })

  it("shows checkmark for passed checks", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    const passedCheck = screen.getByTestId("gate-check-median_rank_ic")
    expect(passedCheck).toHaveTextContent("\u2713")
  })

  it("shows cross for failed checks", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={false} />)
    const failedCheck = screen.getByTestId("gate-check-min_clusters")
    expect(failedCheck).toHaveTextContent("\u2717")
  })

  it("renders check values and thresholds", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={false} />)
    const check = screen.getByTestId("gate-check-median_rank_ic")
    expect(check).toHaveTextContent("0.2300")
    expect(check).toHaveTextContent("0.1500")
  })

  it("uses bullish color for passed gate status", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    const status = screen.getByTestId("gate-status")
    expect(status.className).toContain("text-bullish")
  })

  it("uses bearish color for failed gate status", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={false} />)
    const status = screen.getByTestId("gate-status")
    expect(status.className).toContain("text-bearish")
  })

  it("uses terminal-card class", () => {
    render(<ValidationChecklist checks={mockGateChecks} gatePassed={true} />)
    const container = screen.getByTestId("validation-checklist")
    expect(container.className).toContain("terminal-card")
  })

  it("renders empty state when no checks", () => {
    render(<ValidationChecklist checks={[]} gatePassed={true} />)
    expect(screen.getByText("No gate checks available.")).toBeInTheDocument()
  })
})

// --- Page integration tests ---

vi.mock("@/lib/api/model-validation", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/model-validation")>(
    "@/lib/api/model-validation"
  )
  return {
    ...actual,
    getLatestValidationReport: vi.fn(),
  }
})

import ModelValidationPage from "@/app/admin/model-validation/page"
import { getLatestValidationReport } from "@/lib/api/model-validation"

const mockedGetReport = vi.mocked(getLatestValidationReport)

const mockReport = {
  run_group_id: "abc-123-def",
  created_at: "2026-02-27T10:00:00Z",
  n_seeds: 5,
  gate_passed: true,
  selected_seed: 42,
  metric_distributions: mockDistributions,
  gate_checks: mockGateChecks,
  seed_details: mockSeedDetails,
  environment_snapshot: { python_version: "3.13.5" },
  comparison: null,
}

describe("ModelValidationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders loading state initially", () => {
    mockedGetReport.mockReturnValue(new Promise(() => {})) // never resolves
    render(<ModelValidationPage />)
    expect(screen.getByText("Loading validation report...")).toBeInTheDocument()
  })

  it("renders the full report on success", async () => {
    mockedGetReport.mockResolvedValue(mockReport)
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("summary-header")).toBeInTheDocument()
    })
    expect(screen.getByText("abc-123-def")).toBeInTheDocument()
    expect(screen.getByTestId("gate-badge")).toHaveTextContent("PASSED")
    // "Seed 42" appears in both the summary header and the detail table
    expect(screen.getAllByText(/Seed 42/).length).toBeGreaterThanOrEqual(1)
  })

  it("renders error state on failure", async () => {
    mockedGetReport.mockRejectedValue(new Error("Server error"))
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("error-state")).toBeInTheDocument()
    })
    expect(screen.getByText("Server error")).toBeInTheDocument()
  })

  it("renders empty state when report is null", async () => {
    mockedGetReport.mockRejectedValue(new Error("Not found"))
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("error-state")).toBeInTheDocument()
    })
  })

  it("renders comparison section when present", async () => {
    mockedGetReport.mockResolvedValue({
      ...mockReport,
      comparison: {
        p_value: 0.0042,
        effect_size: 0.45,
        significant: true,
        label: "vs_previous",
        n_compared: 5,
        mean_difference: 0.05,
      },
    })
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("comparison-section")).toBeInTheDocument()
    })
    expect(screen.getByText("vs_previous")).toBeInTheDocument()
    expect(screen.getByText("0.0042")).toBeInTheDocument()
  })

  it("does not render comparison section when null", async () => {
    mockedGetReport.mockResolvedValue(mockReport)
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("summary-header")).toBeInTheDocument()
    })
    expect(screen.queryByTestId("comparison-section")).not.toBeInTheDocument()
  })

  it("shows FAILED badge when gate failed", async () => {
    mockedGetReport.mockResolvedValue({ ...mockReport, gate_passed: false })
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("gate-badge")).toHaveTextContent("FAILED")
    })
  })

  it("shows selected seed info as 'None' when null", async () => {
    mockedGetReport.mockResolvedValue({ ...mockReport, selected_seed: null })
    render(<ModelValidationPage />)
    await waitFor(() => {
      expect(screen.getByTestId("summary-header")).toBeInTheDocument()
    })
    expect(screen.getByText("None")).toBeInTheDocument()
  })
})
