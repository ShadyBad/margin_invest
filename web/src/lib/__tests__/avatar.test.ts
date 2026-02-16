import { describe, it, expect } from "vitest"
import { getInitials, getAvatarColor } from "../avatar"

describe("getInitials", () => {
  it("extracts first and last initials from full name", () => {
    expect(getInitials("Brandon Lee")).toBe("BL")
  })

  it("extracts single initial from single name", () => {
    expect(getInitials("Brandon")).toBe("B")
  })

  it("strips domain from email addresses", () => {
    expect(getInitials("brandon@example.com")).toBe("B")
  })

  it("returns ? for empty string", () => {
    expect(getInitials("")).toBe("?")
  })

  it("returns ? for whitespace-only string", () => {
    expect(getInitials("   ")).toBe("?")
  })

  it("uppercases lowercase initials", () => {
    expect(getInitials("john doe")).toBe("JD")
  })

  it("uses first and last parts for three-word names", () => {
    expect(getInitials("Mary Jane Watson")).toBe("MW")
  })
})

describe("getAvatarColor", () => {
  it("returns the same color for the same identifier (deterministic)", () => {
    const color1 = getAvatarColor("test@example.com")
    const color2 = getAvatarColor("test@example.com")
    expect(color1).toBe(color2)
  })

  it("returns a valid hex color", () => {
    expect(getAvatarColor("test")).toMatch(/^#[0-9a-fA-F]{6}$/)
  })

  it("returns different colors for different identifiers", () => {
    const colors = new Set(
      ["alice", "bob", "charlie", "diana", "eve"].map(getAvatarColor),
    )
    // With 5 inputs and 10 colors, we expect at least 2 distinct colors
    expect(colors.size).toBeGreaterThanOrEqual(2)
  })
})
