import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { SystemDiagram } from "../system-diagram"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    rect: (props: any) => <rect {...props} />,
    text: ({ children, ...props }: any) => <text {...props}>{children}</text>,
    line: (props: any) => <line {...props} />,
    path: (props: any) => <path {...props} />,
    g: ({ children, ...props }: any) => <g {...props}>{children}</g>,
  },
  useInView: () => true,
}))

describe("SystemDiagram", () => {
  it("renders section label", () => {
    render(<SystemDiagram />)
    expect(screen.getByText("How the engine works")).toBeInTheDocument()
  })

  it("renders pipeline stage labels", () => {
    render(<SystemDiagram />)
    // Labels appear in both desktop SVG and mobile card stack
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Quality/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Value/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Momentum/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Composite Score").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Classification").length).toBeGreaterThanOrEqual(1)
  })

  it("renders the caption", () => {
    render(<SystemDiagram />)
    expect(screen.getByText(/every asset passes through the same pipeline/i)).toBeInTheDocument()
  })
})
