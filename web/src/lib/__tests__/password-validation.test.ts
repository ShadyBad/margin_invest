import { describe, it, expect } from "vitest"
import { validatePassword, PASSWORD_RULES, isPasswordValid } from "../password-validation"

describe("PASSWORD_RULES", () => {
  it("exports 5 rules", () => {
    expect(PASSWORD_RULES).toHaveLength(5)
  })
})

describe("validatePassword", () => {
  it("returns all rules failed for empty string", () => {
    const results = validatePassword("")
    expect(results.every((r) => !r.met)).toBe(true)
  })

  it("returns length met for 12+ chars", () => {
    const results = validatePassword("abcdefghijkl")
    const lengthRule = results.find((r) => r.label === "At least 12 characters")
    expect(lengthRule?.met).toBe(true)
  })

  it("returns length not met for 11 chars", () => {
    const results = validatePassword("abcdefghijk")
    const lengthRule = results.find((r) => r.label === "At least 12 characters")
    expect(lengthRule?.met).toBe(false)
  })

  it("detects uppercase", () => {
    const results = validatePassword("A")
    const rule = results.find((r) => r.label === "One uppercase letter")
    expect(rule?.met).toBe(true)
  })

  it("detects lowercase", () => {
    const results = validatePassword("a")
    const rule = results.find((r) => r.label === "One lowercase letter")
    expect(rule?.met).toBe(true)
  })

  it("detects digit", () => {
    const results = validatePassword("1")
    const rule = results.find((r) => r.label === "One digit")
    expect(rule?.met).toBe(true)
  })

  it("detects special character", () => {
    const results = validatePassword("!")
    const rule = results.find((r) => r.label === "One special character")
    expect(rule?.met).toBe(true)
  })

  it("all rules pass for a strong password", () => {
    const results = validatePassword("MyPassword1!")
    expect(results.every((r) => r.met)).toBe(true)
  })

  it("missing uppercase fails only that rule", () => {
    const results = validatePassword("mypassword1!")
    expect(results.find((r) => r.label === "One uppercase letter")?.met).toBe(false)
    expect(results.find((r) => r.label === "One lowercase letter")?.met).toBe(true)
    expect(results.find((r) => r.label === "One digit")?.met).toBe(true)
    expect(results.find((r) => r.label === "One special character")?.met).toBe(true)
  })
})

describe("isPasswordValid", () => {
  it("returns true for a strong password", () => {
    expect(isPasswordValid("MyPassword1!")).toBe(true)
  })

  it("returns false for a weak password", () => {
    expect(isPasswordValid("short")).toBe(false)
  })
})
