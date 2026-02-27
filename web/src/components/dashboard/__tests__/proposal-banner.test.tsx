import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ProposalBanner } from "../proposal-banner"

const mockProposals = [
  {
    id: 1,
    proposal_type: "watchlist_add",
    status: "pending",
    payload: { ticker: "AAPL", rationale: "Strong quality metrics" },
    created_at: "2026-02-27T10:00:00Z",
    decided_at: null,
  },
  {
    id: 2,
    proposal_type: "watchlist_remove",
    status: "pending",
    payload: { ticker: "TSLA", rationale: "Failed momentum filter" },
    created_at: "2026-02-27T11:00:00Z",
    decided_at: null,
  },
]

vi.mock("@/lib/api/proposals", () => ({
  getProposals: vi.fn(),
  acceptProposal: vi.fn(),
  dismissProposal: vi.fn(),
}))

import { getProposals, acceptProposal, dismissProposal } from "@/lib/api/proposals"

const mockedGetProposals = vi.mocked(getProposals)
const mockedAcceptProposal = vi.mocked(acceptProposal)
const mockedDismissProposal = vi.mocked(dismissProposal)

beforeEach(() => {
  vi.clearAllMocks()
})

describe("ProposalBanner", () => {
  it("renders nothing when no proposals", async () => {
    mockedGetProposals.mockResolvedValue({ proposals: [] })
    const { container } = render(<ProposalBanner />)
    await waitFor(() => {
      expect(mockedGetProposals).toHaveBeenCalledWith("pending")
    })
    expect(container.firstChild).toBeNull()
  })

  it("renders proposal cards with type badge and ticker", async () => {
    mockedGetProposals.mockResolvedValue({ proposals: mockProposals })
    render(<ProposalBanner />)
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText("watchlist_add")).toBeInTheDocument()
    expect(screen.getByText("watchlist_remove")).toBeInTheDocument()
  })

  it("accept button calls API and removes proposal from list", async () => {
    const user = userEvent.setup()
    mockedGetProposals.mockResolvedValue({
      proposals: [mockProposals[0]],
    })
    mockedAcceptProposal.mockResolvedValue({ status: "accepted" })

    render(<ProposalBanner />)
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    const acceptBtn = screen.getByRole("button", { name: /accept/i })
    await user.click(acceptBtn)

    await waitFor(() => {
      expect(mockedAcceptProposal).toHaveBeenCalledWith(1)
    })
    await waitFor(() => {
      expect(screen.queryByText("AAPL")).not.toBeInTheDocument()
    })
  })

  it("dismiss button calls API and removes proposal from list", async () => {
    const user = userEvent.setup()
    mockedGetProposals.mockResolvedValue({
      proposals: [mockProposals[1]],
    })
    mockedDismissProposal.mockResolvedValue({ status: "dismissed" })

    render(<ProposalBanner />)
    await waitFor(() => {
      expect(screen.getByText("TSLA")).toBeInTheDocument()
    })

    const dismissBtn = screen.getByRole("button", { name: /dismiss/i })
    await user.click(dismissBtn)

    await waitFor(() => {
      expect(mockedDismissProposal).toHaveBeenCalledWith(2)
    })
    await waitFor(() => {
      expect(screen.queryByText("TSLA")).not.toBeInTheDocument()
    })
  })

  it("shows rationale text from payload", async () => {
    mockedGetProposals.mockResolvedValue({ proposals: mockProposals })
    render(<ProposalBanner />)
    await waitFor(() => {
      expect(screen.getByText("Strong quality metrics")).toBeInTheDocument()
    })
    expect(screen.getByText("Failed momentum filter")).toBeInTheDocument()
  })
})
