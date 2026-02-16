import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { Avatar } from "../avatar"

describe("Avatar", () => {
  it("renders img when avatarUrl is provided", () => {
    render(<Avatar name="Brandon Lee" avatarUrl="https://example.com/avatar.jpg" size="md" />)
    const img = screen.getByRole("img", { name: "Brandon Lee's avatar" })
    expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg")
  })

  it("renders img when only oauthAvatarUrl is provided", () => {
    render(
      <Avatar name="Brandon Lee" oauthAvatarUrl="https://oauth.example.com/photo.jpg" size="md" />,
    )
    const img = screen.getByRole("img", { name: "Brandon Lee's avatar" })
    expect(img).toHaveAttribute("src", "https://oauth.example.com/photo.jpg")
  })

  it("renders SVG with initials when no URLs provided", () => {
    const { container } = render(<Avatar name="Brandon Lee" size="md" />)
    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const text = container.querySelector("text")
    expect(text).toHaveTextContent("BL")
  })

  it("falls back to initials SVG when img onError fires", () => {
    const { container } = render(
      <Avatar name="Brandon Lee" avatarUrl="https://example.com/broken.jpg" size="md" />,
    )
    const img = screen.getByRole("img", { name: "Brandon Lee's avatar" })
    fireEvent.error(img)

    const svg = container.querySelector("svg")
    expect(svg).toBeInTheDocument()
    const text = container.querySelector("text")
    expect(text).toHaveTextContent("BL")
  })

  it("renders correct size for sm (24px)", () => {
    const { container } = render(<Avatar name="Brandon Lee" size="sm" />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("width", "24")
    expect(svg).toHaveAttribute("height", "24")
  })

  it("renders correct size for lg (48px)", () => {
    const { container } = render(<Avatar name="Brandon Lee" size="lg" />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveAttribute("width", "48")
    expect(svg).toHaveAttribute("height", "48")
  })

  it("prefers avatarUrl over oauthAvatarUrl", () => {
    render(
      <Avatar
        name="Brandon Lee"
        avatarUrl="https://custom.com/avatar.jpg"
        oauthAvatarUrl="https://oauth.com/photo.jpg"
        size="md"
      />,
    )
    const img = screen.getByRole("img", { name: "Brandon Lee's avatar" })
    expect(img).toHaveAttribute("src", "https://custom.com/avatar.jpg")
  })
})
