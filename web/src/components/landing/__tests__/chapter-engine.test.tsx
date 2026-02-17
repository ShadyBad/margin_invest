import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
  },
  useInView: () => true,
}))

import { ChapterEngine } from "../chapter-engine"

describe("ChapterEngine", () => {
  it("renders three panels", () => {
    const { container } = render(<ChapterEngine />)
    const panels = container.querySelectorAll("[data-engine-panel]")
    expect(panels).toHaveLength(3)
  })

  it("renders Raw Signal panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/raw signal/i)).toBeDefined()
  })

  it("renders Structured Analysis panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/structured analysis/i)).toBeDefined()
  })

  it("renders Conviction Output panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/conviction output/i)).toBeDefined()
  })
})
