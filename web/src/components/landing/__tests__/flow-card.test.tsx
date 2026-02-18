import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, style, ...props }: any) => (
      <div style={style} {...props}>{children}</div>
    ),
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, inputOrFn: number[] | Function, output?: any[]) => {
    if (typeof inputOrFn === "function") return inputOrFn(0)
    return output![Math.floor(output!.length / 2)]
  },
  useReducedMotion: () => false,
}))

import { FlowCard } from "../flow-card"

describe("FlowCard", () => {
  it("renders children inside a glass surface", () => {
    render(
      <FlowCard title="Raw Signal" subtitle="The Engine">
        <p>Test content</p>
      </FlowCard>,
    )
    expect(screen.getByText("Raw Signal")).toBeInTheDocument()
    expect(screen.getByText("The Engine")).toBeInTheDocument()
    expect(screen.getByText("Test content")).toBeInTheDocument()
  })

  it("renders with data-flow-card attribute", () => {
    const { container } = render(
      <FlowCard title="Test" subtitle="Sub">
        <p>Content</p>
      </FlowCard>,
    )
    expect(container.querySelector("[data-flow-card]")).toBeInTheDocument()
  })
})
