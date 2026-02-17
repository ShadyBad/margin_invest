import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { CustomCrosshair } from "../custom-crosshair"

describe("CustomCrosshair", () => {
  it("renders nothing when not active", () => {
    const { container } = render(<CustomCrosshair active={false} payload={[]} label="" />)
    expect(container.firstChild).toBeNull()
  })

  it("renders date, close, volume when active with payload", () => {
    const payload = [
      { dataKey: "close", value: 182.5, color: "#1C7A5A" },
      { dataKey: "volume", value: 45000000, color: "#888" },
    ]
    render(<CustomCrosshair active={true} payload={payload} label="02-14" />)
    expect(screen.getByText("02-14")).toBeInTheDocument()
    expect(screen.getByText("$182.50")).toBeInTheDocument()
    expect(screen.getByText("45.0M")).toBeInTheDocument()
  })

  it("formats volume in millions", () => {
    const payload = [
      { dataKey: "close", value: 100, color: "#1C7A5A" },
      { dataKey: "volume", value: 1234567, color: "#888" },
    ]
    render(<CustomCrosshair active={true} payload={payload} label="01-01" />)
    expect(screen.getByText("1.2M")).toBeInTheDocument()
  })
})
