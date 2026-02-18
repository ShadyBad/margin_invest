import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

import { PipelineDiagram } from "../pipeline-diagram"

describe("PipelineDiagram", () => {
  it("renders all 6 pipeline stages", () => {
    render(<PipelineDiagram activeStage={0} />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("FILTER")).toBeInTheDocument()
    expect(screen.getByText("FACTOR MODEL")).toBeInTheDocument()
    expect(screen.getByText("NORMALIZE")).toBeInTheDocument()
    expect(screen.getByText("SCORE")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("highlights the active stage", () => {
    const { container } = render(<PipelineDiagram activeStage={2} />)
    const stages = container.querySelectorAll("[data-pipeline-stage]")
    expect(stages[2]).toHaveAttribute("data-active", "true")
  })
})
