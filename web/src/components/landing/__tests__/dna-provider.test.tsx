import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"
import { DNAProvider } from "../dna-provider"

describe("DNAProvider", () => {
  it("renders children", () => {
    const { getByText } = render(
      <DNAProvider>
        <div>child content</div>
      </DNAProvider>,
    )
    expect(getByText("child content")).toBeDefined()
  })

  it("injects CSS custom properties on document element when dna prop provided", () => {
    render(
      <DNAProvider
        dna={{
          base: "#1A3A5C",
          mid: "#0E4F4F",
          accent: "#1A7A5A",
          density: 0.6,
          tempo: 0.85,
        }}
      >
        <div>content</div>
      </DNAProvider>,
    )
    const style = document.documentElement.style
    expect(style.getPropertyValue("--dna-base")).toBe("#1A3A5C")
    expect(style.getPropertyValue("--dna-mid")).toBe("#0E4F4F")
    expect(style.getPropertyValue("--dna-accent")).toBe("#1A7A5A")
    expect(style.getPropertyValue("--dna-density")).toBe("0.6")
    expect(style.getPropertyValue("--dna-tempo")).toBe("0.85")
  })

  it("renders without dna prop (unauthenticated)", () => {
    const { getByText } = render(
      <DNAProvider>
        <div>no dna</div>
      </DNAProvider>,
    )
    expect(getByText("no dna")).toBeDefined()
  })
})
