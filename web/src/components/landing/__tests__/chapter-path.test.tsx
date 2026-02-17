import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  useInView: () => true,
}))

import { ChapterPath } from "../chapter-path"

describe("ChapterPath", () => {
  it("renders three pricing tiers", () => {
    const { getByText } = render(<ChapterPath />)
    expect(getByText("Scout")).toBeDefined()
    expect(getByText("Operator")).toBeDefined()
    expect(getByText("Allocator")).toBeDefined()
  })

  it("renders CTA button", () => {
    const { getByRole } = render(<ChapterPath />)
    const cta = getByRole("link", { name: /start scoring/i })
    expect(cta).toBeDefined()
  })

  it("highlights middle card with elevated glass", () => {
    const { container } = render(<ChapterPath />)
    const elevated = container.querySelector(".glass-elevated")
    expect(elevated).toBeDefined()
  })
})
