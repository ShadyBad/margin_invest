import { describe, it, expect } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { SectorNeutralBanner } from "../sector-neutral-banner"

describe("SectorNeutralBanner", () => {
  it("renders sector name and code", () => {
    render(<SectorNeutralBanner sectorName="Technology" sectorCode="4510" />)
    const banner = screen.getByTestId("sector-neutral-banner")
    expect(banner).toBeInTheDocument()
    expect(banner).toHaveTextContent("Technology")
    expect(banner).toHaveTextContent("GICS 4510")
  })

  it("renders without sector code", () => {
    render(<SectorNeutralBanner sectorName="Financials" />)
    const banner = screen.getByTestId("sector-neutral-banner")
    expect(banner).toHaveTextContent("Financials")
    expect(banner).not.toHaveTextContent("GICS")
  })

  it("shows why tooltip on hover of Why? text", async () => {
    render(<SectorNeutralBanner sectorName="Technology" sectorCode="4510" />)
    const whyLink = screen.getByText("Why?")
    fireEvent.mouseEnter(whyLink)

    await waitFor(() => {
      expect(
        screen.getByText(/Sector-neutral ranking ensures fair comparison/)
      ).toBeInTheDocument()
    })
  })

  it("hides why tooltip on mouse leave", async () => {
    render(<SectorNeutralBanner sectorName="Technology" sectorCode="4510" />)
    const whyLink = screen.getByText("Why?")

    fireEvent.mouseEnter(whyLink)
    await waitFor(() => {
      expect(
        screen.getByText(/Sector-neutral ranking ensures fair comparison/)
      ).toBeInTheDocument()
    })

    fireEvent.mouseLeave(whyLink)
    await waitFor(() => {
      expect(
        screen.queryByText(/Sector-neutral ranking ensures fair comparison/)
      ).not.toBeInTheDocument()
    })
  })
})
