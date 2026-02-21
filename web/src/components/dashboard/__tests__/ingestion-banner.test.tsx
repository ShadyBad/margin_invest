import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { IngestionBanner } from "../ingestion-banner"

describe("IngestionBanner", () => {
  it("renders nothing when universe is complete", () => {
    const { container } = render(
      <IngestionBanner
        universe={{
          version: "v1",
          size: 5000,
          scoring_coverage: 0.98,
          is_complete: true,
          last_scoring_run: null,
        }}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders warning when coverage between 50-95%", () => {
    render(
      <IngestionBanner
        universe={{
          version: "v1",
          size: 5000,
          scoring_coverage: 0.72,
          is_complete: false,
          last_scoring_run: null,
        }}
      />
    )
    expect(screen.getByText(/72%/)).toBeInTheDocument()
    expect(screen.getByText(/Rankings may shift/)).toBeInTheDocument()
  })

  it("renders error when coverage below 50%", () => {
    render(
      <IngestionBanner
        universe={{
          version: "v1",
          size: 5000,
          scoring_coverage: 0.3,
          is_complete: false,
          last_scoring_run: null,
        }}
      />
    )
    expect(screen.getByText(/30%/)).toBeInTheDocument()
    expect(screen.getByText(/Rankings may shift/)).toBeInTheDocument()
  })
})
