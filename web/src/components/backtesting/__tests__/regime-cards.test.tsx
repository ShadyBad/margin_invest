import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { RegimeCards } from "../regime-cards"
import type { RegimePerformance } from "../regime-cards"

const mockRegimes: RegimePerformance[] = [
  {
    regime: "bull",
    label: "Bull Market",
    modelReturn: 0.18,
    benchmarkReturn: 0.12,
    months: 36,
    excessReturn: 0.06,
  },
  {
    regime: "bear",
    label: "Bear Market",
    modelReturn: -0.05,
    benchmarkReturn: -0.15,
    months: 12,
    excessReturn: 0.1,
  },
  {
    regime: "sideways",
    label: "Sideways",
    modelReturn: 0.04,
    benchmarkReturn: 0.03,
    months: 24,
    excessReturn: 0.01,
  },
  {
    regime: "crisis",
    label: "Crisis",
    modelReturn: -0.25,
    benchmarkReturn: -0.2,
    months: 6,
    excessReturn: -0.05,
  },
]

describe("RegimeCards", () => {
  it("renders all four regime cards when given 4 regimes", () => {
    render(<RegimeCards regimes={mockRegimes} />)
    const container = screen.getByTestId("regime-cards")
    expect(container).toBeInTheDocument()

    expect(screen.getByTestId("regime-card-bull")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-bear")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-sideways")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-crisis")).toBeInTheDocument()
  })

  it("shows correct model return percentage formatting", () => {
    render(<RegimeCards regimes={mockRegimes} />)

    // Bull: 0.18 -> +18.0%
    const bullCard = screen.getByTestId("regime-card-bull")
    expect(bullCard.textContent).toContain("+18.0%")

    // Bear: -0.05 -> -5.0%
    const bearCard = screen.getByTestId("regime-card-bear")
    expect(bearCard.textContent).toContain("-5.0%")

    // Crisis: -0.25 -> -25.0%
    const crisisCard = screen.getByTestId("regime-card-crisis")
    expect(crisisCard.textContent).toContain("-25.0%")
  })

  it("shows correct excess return with sign and color", () => {
    render(<RegimeCards regimes={mockRegimes} />)

    // Bull: excess +0.06 -> +6.0% (positive = bullish color)
    const bullExcess = screen.getByTestId("regime-excess-bull")
    expect(bullExcess.textContent).toContain("+6.0%")
    expect(bullExcess.className).toContain("text-bullish")

    // Crisis: excess -0.05 -> -5.0% (negative = bearish color)
    const crisisExcess = screen.getByTestId("regime-excess-crisis")
    expect(crisisExcess.textContent).toContain("-5.0%")
    expect(crisisExcess.className).toContain("text-bearish")
  })

  it("shows month count for each regime", () => {
    render(<RegimeCards regimes={mockRegimes} />)

    const bullCard = screen.getByTestId("regime-card-bull")
    expect(bullCard.textContent).toContain("36")

    const bearCard = screen.getByTestId("regime-card-bear")
    expect(bearCard.textContent).toContain("12")

    const sidewaysCard = screen.getByTestId("regime-card-sideways")
    expect(sidewaysCard.textContent).toContain("24")

    const crisisCard = screen.getByTestId("regime-card-crisis")
    expect(crisisCard.textContent).toContain("6")
  })

  it("handles empty regimes array gracefully", () => {
    render(<RegimeCards regimes={[]} />)
    const container = screen.getByTestId("regime-cards-empty")
    expect(container).toBeInTheDocument()
    expect(screen.queryByTestId("regime-card-bull")).not.toBeInTheDocument()
  })

  it("shows benchmark return for each regime", () => {
    render(<RegimeCards regimes={mockRegimes} />)

    const bullBenchmark = screen.getByTestId("regime-benchmark-bull")
    expect(bullBenchmark.textContent).toContain("+12.0%")

    const bearBenchmark = screen.getByTestId("regime-benchmark-bear")
    expect(bearBenchmark.textContent).toContain("-15.0%")
  })

  it("shows regime labels", () => {
    render(<RegimeCards regimes={mockRegimes} />)
    expect(screen.getByText("Bull Market")).toBeInTheDocument()
    expect(screen.getByText("Bear Market")).toBeInTheDocument()
    expect(screen.getByText("Sideways")).toBeInTheDocument()
    expect(screen.getByText("Crisis")).toBeInTheDocument()
  })
})
