import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectionWrapper } from "../section-wrapper"
import { ButtonPrimary } from "../button-primary"
import { ButtonSecondary } from "../button-secondary"
import { Divider } from "../divider"
import { CapabilityBlock } from "../capability-block"
import { UIImageFrame } from "../ui-image-frame"
import { DiagramNodeLabel } from "../diagram-node-label"

describe("SectionWrapper", () => {
  it("renders children within max-width container", () => {
    render(<SectionWrapper id="test"><p>Content</p></SectionWrapper>)
    expect(screen.getByText("Content")).toBeInTheDocument()
  })
})

describe("ButtonPrimary", () => {
  it("renders as a link with accent styling", () => {
    render(<ButtonPrimary href="/test">Click me</ButtonPrimary>)
    const link = screen.getByRole("link", { name: "Click me" })
    expect(link).toHaveAttribute("href", "/test")
  })
})

describe("ButtonSecondary", () => {
  it("renders as a text link", () => {
    render(<ButtonSecondary href="/test">Learn more</ButtonSecondary>)
    const link = screen.getByRole("link", { name: "Learn more" })
    expect(link).toHaveAttribute("href", "/test")
  })
})

describe("Divider", () => {
  it("renders a horizontal rule", () => {
    render(<Divider />)
    expect(screen.getByRole("separator")).toBeInTheDocument()
  })
})

describe("CapabilityBlock", () => {
  it("renders title and description", () => {
    render(<CapabilityBlock title="Test Title" description="Test desc" />)
    expect(screen.getByText("Test Title")).toBeInTheDocument()
    expect(screen.getByText("Test desc")).toBeInTheDocument()
  })

  it("applies tinted background when tinted prop is true", () => {
    const { container } = render(
      <CapabilityBlock title="Tinted" description="desc" tinted />
    )
    expect(container.firstChild).toHaveClass("bg-bg-subtle")
  })
})

describe("UIImageFrame", () => {
  it("renders an image with border styling", () => {
    render(<UIImageFrame src="/test.png" alt="Test image" />)
    const img = screen.getByAltText("Test image")
    expect(img).toHaveAttribute("src", "/test.png")
  })
})

describe("DiagramNodeLabel", () => {
  it("renders the label text", () => {
    render(<DiagramNodeLabel label="Market Data" active={false} />)
    expect(screen.getByText("Market Data")).toBeInTheDocument()
  })

  it("applies accent color when active", () => {
    const { container } = render(
      <DiagramNodeLabel label="Market Data" active />
    )
    expect(container.firstChild).toHaveClass("text-accent")
  })
})
