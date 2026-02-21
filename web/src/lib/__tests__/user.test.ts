import { describe, it, expect } from "vitest"
import { getDisplayName } from "../user"

describe("getDisplayName", () => {
  it("returns email prefix for standard email", () => {
    expect(getDisplayName({ email: "bpshay13@gmail.com" })).toBe("bpshay13")
  })

  it("prefers user.name over email prefix", () => {
    expect(getDisplayName({ name: "Brandon", email: "bpshay13@gmail.com" })).toBe("Brandon")
  })

  it("ignores whitespace-only name", () => {
    expect(getDisplayName({ name: "   ", email: "bpshay13@gmail.com" })).toBe("bpshay13")
  })

  it("falls back to User when email is missing", () => {
    expect(getDisplayName({})).toBe("User")
  })

  it("falls back to User when email prefix is empty", () => {
    expect(getDisplayName({ email: "@domain.com" })).toBe("User")
  })

  it("falls back to User for undefined email", () => {
    expect(getDisplayName({ email: undefined })).toBe("User")
  })

  it("truncates names longer than 20 characters", () => {
    expect(getDisplayName({ email: "averylongemailprefix123@example.com" })).toBe(
      "averylongemailprefix…"
    )
  })

  it("does not truncate names exactly 20 characters", () => {
    expect(getDisplayName({ email: "exactly20characters!@example.com" })).toBe(
      "exactly20characters!"
    )
  })

  it("ignores empty string name", () => {
    expect(getDisplayName({ name: "", email: "test@example.com" })).toBe("test")
  })

  it("truncates long user.name too", () => {
    expect(getDisplayName({ name: "A Very Long Display Name Here" })).toBe("A Very Long Display …")
  })
})
