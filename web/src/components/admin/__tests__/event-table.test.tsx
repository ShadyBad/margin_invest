import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { EventTable } from "../event-table"

const mockEvents = [
  {
    id: 1,
    event_type: "score_publish",
    source: "publish_scores",
    detail: { ticker_count: 150, batch_id: "abc-123" },
    created_at: "2026-02-27T10:00:00Z",
  },
  {
    id: 2,
    event_type: "ml_model_deploy",
    source: "deploy_ml_model",
    detail: { model_version: "v4.2", rank_ic: 0.28 },
    created_at: "2026-02-27T09:30:00Z",
  },
  {
    id: 3,
    event_type: "universe_activation",
    source: "activate_universe",
    detail: null,
    created_at: "2026-02-27T09:00:00Z",
  },
]

vi.mock("@/lib/api/governance", () => ({
  getEvents: vi.fn(),
}))

import { getEvents } from "@/lib/api/governance"

const mockedGetEvents = vi.mocked(getEvents)

beforeEach(() => {
  vi.clearAllMocks()
  mockedGetEvents.mockResolvedValue({ events: mockEvents, total: 3 })
})

describe("EventTable", () => {
  it("renders event rows with correct event_type and source", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })
    expect(screen.getByText("publish_scores")).toBeInTheDocument()
    expect(screen.getByText("ml_model_deploy")).toBeInTheDocument()
    expect(screen.getByText("deploy_ml_model")).toBeInTheDocument()
    expect(screen.getByText("universe_activation")).toBeInTheDocument()
    expect(screen.getByText("activate_universe")).toBeInTheDocument()
  })

  it("renders detail as truncated JSON", async () => {
    mockedGetEvents.mockResolvedValue({
      events: [
        {
          id: 10,
          event_type: "test_event",
          source: "test_source",
          detail: {
            very_long_key: "a".repeat(200),
          },
          created_at: "2026-02-27T10:00:00Z",
        },
      ],
      total: 1,
    })
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("test_event")).toBeInTheDocument()
    })
    // Detail should be truncated — the cell should not contain the full 200-char string
    const detailCell = screen.getByTestId("event-detail-10")
    expect(detailCell.textContent!.length).toBeLessThanOrEqual(103) // 100 chars + "..."
  })

  it("renders null detail as dash", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("universe_activation")).toBeInTheDocument()
    })
    const detailCell = screen.getByTestId("event-detail-3")
    expect(detailCell).toHaveTextContent("\u2014")
  })

  it("shows pagination controls", async () => {
    mockedGetEvents.mockResolvedValue({ events: mockEvents, total: 120 })
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /previous/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument()
    expect(screen.getByText("1\u201350 of 120")).toBeInTheDocument()
  })

  it("shows empty state when no events", async () => {
    mockedGetEvents.mockResolvedValue({ events: [], total: 0 })
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText(/no events/i)).toBeInTheDocument()
    })
  })

  it("filter input triggers new fetch", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(mockedGetEvents).toHaveBeenCalledTimes(1)
    })

    const filterInput = screen.getByPlaceholderText(/filter by event type/i)
    fireEvent.change(filterInput, { target: { value: "score" } })

    await waitFor(() => {
      expect(mockedGetEvents).toHaveBeenCalledWith("test-key", {
        event_type: "score",
        limit: 50,
        offset: 0,
      })
    })
  })

  it("passes adminKey to getEvents", async () => {
    render(<EventTable adminKey="my-admin-key" />)
    await waitFor(() => {
      expect(mockedGetEvents).toHaveBeenCalledWith("my-admin-key", {
        event_type: "",
        limit: 50,
        offset: 0,
      })
    })
  })

  it("disables Previous button on first page", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled()
  })

  it("disables Next button on last page", async () => {
    mockedGetEvents.mockResolvedValue({ events: mockEvents, total: 3 })
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled()
  })

  it("advances to next page and fetches with offset", async () => {
    mockedGetEvents.mockResolvedValue({ events: mockEvents, total: 120 })
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole("button", { name: /next/i }))

    await waitFor(() => {
      expect(mockedGetEvents).toHaveBeenCalledWith("test-key", {
        event_type: "",
        limit: 50,
        offset: 50,
      })
    })
  })

  it("uses terminal-card class on container", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByTestId("event-table")).toBeInTheDocument()
    })
    expect(screen.getByTestId("event-table").className).toContain("terminal-card")
  })

  it("uses monospace font for event type cells", async () => {
    render(<EventTable adminKey="test-key" />)
    await waitFor(() => {
      expect(screen.getByText("score_publish")).toBeInTheDocument()
    })
    const cell = screen.getByTestId("event-type-1")
    expect(cell.className).toContain("font-mono")
  })
})
