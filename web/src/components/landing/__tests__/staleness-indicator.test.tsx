import { render, screen } from "@testing-library/react"
import { StalenessIndicator } from "../shared/staleness-indicator"

test("renders staleness indicator when using fallback data", () => {
  render(<StalenessIndicator isFallback={true} />)
  expect(screen.getByText(/sample data/i)).toBeInTheDocument()
})

test("hides staleness indicator with live data", () => {
  const { container } = render(<StalenessIndicator isFallback={false} />)
  expect(container).toBeEmptyDOMElement()
})

test("hides staleness indicator when isFallback is undefined", () => {
  const { container } = render(<StalenessIndicator />)
  expect(container).toBeEmptyDOMElement()
})
