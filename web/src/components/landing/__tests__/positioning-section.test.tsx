// web/src/components/landing/__tests__/positioning-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
  },
}))

import { PositioningSection } from "../positioning-section"

describe("PositioningSection", () => {
  it("renders headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()
  })

  it("renders not-for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Day traders")).toBeInTheDocument()
    expect(screen.getByText("Narrative chasers")).toBeInTheDocument()
    expect(screen.getByText("Meme cycles")).toBeInTheDocument()
  })

  it("renders for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Long-horizon investors")).toBeInTheDocument()
    expect(screen.getByText("Portfolio operators")).toBeInTheDocument()
    expect(screen.getByText("Capital stewards")).toBeInTheDocument()
  })
})
