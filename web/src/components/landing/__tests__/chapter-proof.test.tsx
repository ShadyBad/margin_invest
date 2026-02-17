import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  useInView: () => true,
}))

import { ChapterProof } from "../chapter-proof"

describe("ChapterProof", () => {
  it("renders three panels", () => {
    const { container } = render(<ChapterProof />)
    const panels = container.querySelectorAll("[data-proof-panel]")
    expect(panels).toHaveLength(3)
  })

  it("renders Sample Analysis panel", () => {
    const { getByText } = render(<ChapterProof />)
    expect(getByText(/sample analysis/i)).toBeDefined()
  })

  it("renders Factor Depth panel", () => {
    const { getByText } = render(<ChapterProof />)
    expect(getByText(/factor depth/i)).toBeDefined()
  })

  it("renders Portfolio View panel", () => {
    const { getByText } = render(<ChapterProof />)
    expect(getByText(/portfolio view/i)).toBeDefined()
  })
})
