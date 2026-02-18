import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { EngineCard } from "../engine-card"

describe("EngineCard", () => {
  it("renders title and subtitle", () => {
    render(<EngineCard title="Raw Market Signal" subtitle="Input" description="Test desc" />)
    expect(screen.getByText("Raw Market Signal")).toBeInTheDocument()
    expect(screen.getByText("Input")).toBeInTheDocument()
  })

  it("renders description", () => {
    render(<EngineCard title="Test" subtitle="Sub" description="Some description text" />)
    expect(screen.getByText("Some description text")).toBeInTheDocument()
  })
})
