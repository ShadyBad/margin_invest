import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ApprovalCard } from "../approval-card"
import type { Approval } from "@/lib/api/governance"

const stagedApproval: Approval = {
  id: 1,
  gate_type: "score_publish",
  status: "staged",
  pipeline_id: "pipeline-abc",
  payload_ref: { batch_id: 42 },
  impact_summary: {
    ticker_count: 150,
    conviction_changes: 12,
    rank_ic: 0.23,
    added: ["AAPL", "MSFT"],
    removed: ["TSLA"],
  },
  submitted_at: "2026-02-27T10:00:00Z",
  decided_at: null,
  decided_by: null,
  decision_reason: null,
  expires_at: "2026-02-28T10:00:00Z",
}

const approvedApproval: Approval = {
  id: 2,
  gate_type: "ml_model_deploy",
  status: "approved",
  pipeline_id: "pipeline-xyz",
  payload_ref: null,
  impact_summary: {
    ticker_count: 80,
    conviction_changes: 5,
    rank_ic: 0.31,
  },
  submitted_at: "2026-02-26T08:00:00Z",
  decided_at: "2026-02-26T09:00:00Z",
  decided_by: 1,
  decision_reason: "Rank IC above threshold",
  expires_at: null,
}

const rejectedApproval: Approval = {
  id: 3,
  gate_type: "universe_activation",
  status: "rejected",
  pipeline_id: null,
  payload_ref: null,
  impact_summary: null,
  submitted_at: "2026-02-25T12:00:00Z",
  decided_at: "2026-02-25T13:00:00Z",
  decided_by: 1,
  decision_reason: "Scores look off",
  expires_at: null,
}

const expiredApproval: Approval = {
  id: 4,
  gate_type: "score_publish",
  status: "expired",
  pipeline_id: null,
  payload_ref: null,
  impact_summary: { ticker_count: 50 },
  submitted_at: "2026-02-20T10:00:00Z",
  decided_at: null,
  decided_by: null,
  decision_reason: null,
  expires_at: "2026-02-21T10:00:00Z",
}

describe("ApprovalCard", () => {
  it("renders gate_type badge text", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText("score_publish")).toBeInTheDocument()
  })

  it("renders staged status badge with warning styling", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    const badge = screen.getByTestId("status-badge")
    expect(badge).toHaveTextContent("staged")
    expect(badge.className).toContain("text-warning")
  })

  it("renders approved status badge with bullish styling", () => {
    render(
      <ApprovalCard
        approval={approvedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    const badge = screen.getByTestId("status-badge")
    expect(badge).toHaveTextContent("approved")
    expect(badge.className).toContain("text-bullish")
  })

  it("renders rejected status badge with bearish styling", () => {
    render(
      <ApprovalCard
        approval={rejectedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    const badge = screen.getByTestId("status-badge")
    expect(badge).toHaveTextContent("rejected")
    expect(badge.className).toContain("text-bearish")
  })

  it("renders expired status badge with bearish styling", () => {
    render(
      <ApprovalCard
        approval={expiredApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    const badge = screen.getByTestId("status-badge")
    expect(badge).toHaveTextContent("expired")
    expect(badge.className).toContain("text-bearish")
  })

  it("shows impact summary text with ticker count and conviction changes", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText(/150 tickers/)).toBeInTheDocument()
    expect(screen.getByText(/12 conviction changes/)).toBeInTheDocument()
  })

  it("shows rank IC in impact summary", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText(/Rank IC: 0.23/)).toBeInTheDocument()
  })

  it("shows added and removed tickers", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText(/Added: AAPL, MSFT/)).toBeInTheDocument()
    expect(screen.getByText(/Removed: TSLA/)).toBeInTheDocument()
  })

  it("shows approve and reject buttons for staged status", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument()
  })

  it("hides approve and reject buttons for approved status", () => {
    render(
      <ApprovalCard
        approval={approvedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument()
  })

  it("hides approve and reject buttons for rejected status", () => {
    render(
      <ApprovalCard
        approval={rejectedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument()
  })

  it("hides approve and reject buttons for expired status", () => {
    render(
      <ApprovalCard
        approval={expiredApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument()
  })

  it("calls onApprove with correct id when approve button clicked", () => {
    const onApprove = vi.fn()
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={onApprove}
        onReject={vi.fn()}
      />
    )
    fireEvent.click(screen.getByRole("button", { name: /approve/i }))
    expect(onApprove).toHaveBeenCalledWith(1)
  })

  it("calls onReject with correct id when reject button clicked", () => {
    const onReject = vi.fn()
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={onReject}
      />
    )
    fireEvent.click(screen.getByRole("button", { name: /reject/i }))
    expect(onReject).toHaveBeenCalledWith(1)
  })

  it("shows decision reason for decided approvals", () => {
    render(
      <ApprovalCard
        approval={approvedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText(/Rank IC above threshold/)).toBeInTheDocument()
  })

  it("shows decision reason for rejected approvals", () => {
    render(
      <ApprovalCard
        approval={rejectedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.getByText(/Scores look off/)).toBeInTheDocument()
  })

  it("does not show impact summary when null", () => {
    const noImpact: Approval = {
      ...stagedApproval,
      impact_summary: null,
    }
    render(
      <ApprovalCard
        approval={noImpact}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    expect(screen.queryByText(/tickers/)).not.toBeInTheDocument()
  })

  it("renders the card with terminal-card class", () => {
    render(
      <ApprovalCard
        approval={stagedApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />
    )
    const card = screen.getByTestId("approval-card-1")
    expect(card.className).toContain("terminal-card")
  })
})
