import { render, screen } from "@testing-library/react"
import { DashboardGreeting } from "../dashboard-greeting"

describe("DashboardGreeting", () => {
  beforeEach(() => {
    // Default to morning (9 AM)
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 2, 9, 9, 0, 0))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("renders greeting with name in the morning", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("Good morning, Brandon.")).toBeInTheDocument()
  })

  it("renders afternoon greeting", () => {
    vi.setSystemTime(new Date(2026, 2, 9, 14, 0, 0))
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("Good afternoon, Brandon.")).toBeInTheDocument()
  })

  it("renders evening greeting", () => {
    vi.setSystemTime(new Date(2026, 2, 9, 19, 0, 0))
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("Good evening, Brandon.")).toBeInTheDocument()
  })

  it("shows change count when > 0", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={2} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("2 scores changed since yesterday.")).toBeInTheDocument()
  })

  it("shows singular form for 1 change", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={1} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("1 score changed since yesterday.")).toBeInTheDocument()
  })

  it("shows no changes message when count is 0", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("No score changes since yesterday.")).toBeInTheDocument()
  })

  it("shows last updated timestamp", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
  })

  it("handles empty userName gracefully", () => {
    render(
      <DashboardGreeting userName="" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByText("Good morning.")).toBeInTheDocument()
  })

  it("has data-testid on root div", () => {
    render(
      <DashboardGreeting userName="Brandon" changesCount={0} lastUpdated="2026-03-09T08:00:00Z" />
    )
    expect(screen.getByTestId("dashboard-greeting")).toBeInTheDocument()
  })
})
