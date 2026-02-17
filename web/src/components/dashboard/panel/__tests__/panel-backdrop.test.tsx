import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PanelBackdrop } from "../panel-backdrop"

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    motion: {
      ...actual.motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

describe("PanelBackdrop", () => {
  it("calls onClose when clicked", () => {
    const onClose = vi.fn()
    render(<PanelBackdrop onClose={onClose} />)
    fireEvent.click(screen.getByTestId("panel-backdrop"))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("renders with correct aria attributes", () => {
    render(<PanelBackdrop onClose={vi.fn()} />)
    const el = screen.getByTestId("panel-backdrop")
    expect(el).toHaveAttribute("aria-hidden", "true")
  })
})
