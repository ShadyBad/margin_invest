import { render, screen } from "@testing-library/react"
import { PortfolioConviction } from "../portfolio-conviction"

describe("PortfolioConviction", () => {
  it("renders the portfolio score", () => {
    render(<PortfolioConviction score={74} label="Operating" />)
    expect(screen.getByText("74")).toBeInTheDocument()
    expect(screen.getByText("Operating")).toBeInTheDocument()
  })

  it("renders Operating label for scores >= 60", () => {
    render(<PortfolioConviction score={65} label="Operating" />)
    expect(screen.getByText("Operating")).toBeInTheDocument()
  })

  it("renders Building label for scores 30-59", () => {
    render(<PortfolioConviction score={45} label="Building" />)
    expect(screen.getByText("Building")).toBeInTheDocument()
  })

  it("renders Reviewing label for scores < 30", () => {
    render(<PortfolioConviction score={20} label="Reviewing" />)
    expect(screen.getByText("Reviewing")).toBeInTheDocument()
  })

  it("renders nothing when score is null", () => {
    const { container } = render(<PortfolioConviction score={null} label={null} />)
    expect(container.firstChild).toBeNull()
  })
})
