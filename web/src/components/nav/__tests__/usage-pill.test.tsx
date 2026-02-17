import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { UsagePill } from "../usage-pill"

describe("UsagePill", () => {
  it("renders usage count", () => {
    render(<UsagePill used={1} limit={3} />)
    expect(screen.getByText("1/3")).toBeInTheDocument()
  })

  it("shows warning style when limit reached", () => {
    render(<UsagePill used={3} limit={3} />)
    const pill = screen.getByTestId("usage-pill")
    expect(pill.className).toContain("text-warning")
  })

  it("shows accent style when under limit", () => {
    render(<UsagePill used={1} limit={3} />)
    const pill = screen.getByTestId("usage-pill")
    expect(pill.className).toContain("text-accent")
  })

  it("renders nothing for unlimited plans", () => {
    const { container } = render(<UsagePill used={0} limit={null} />)
    expect(container.firstChild).toBeNull()
  })
})
