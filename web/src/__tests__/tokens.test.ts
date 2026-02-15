import { describe, it, expect } from "vitest"
import { colors, fonts, spacing } from "@/styles/tokens"

describe("Design Tokens", () => {
  describe("light mode colors", () => {
    it("defines background tokens", () => {
      expect(colors.light.bgPrimary).toBe("#F4F3EF")
      expect(colors.light.bgElevated).toBe("#FFFFFF")
      expect(colors.light.bgSubtle).toBe("#ECEAE4")
    })

    it("defines text tokens", () => {
      expect(colors.light.textPrimary).toBe("#121212")
      expect(colors.light.textSecondary).toBe("#4A4A4A")
      expect(colors.light.textTertiary).toBe("#8A8A86")
    })

    it("defines accent tokens", () => {
      expect(colors.light.accent).toBe("#0E4F3A")
      expect(colors.light.accentHover).toBe("#0B3E2E")
    })

    it("defines border tokens", () => {
      expect(colors.light.borderPrimary).toBe("#D8D6D0")
    })

    it("defines semantic tokens", () => {
      expect(colors.light.danger).toBe("#C74B50")
      expect(colors.light.warning).toBe("#B8860B")
    })

    it("defines grid and divider tokens", () => {
      expect(colors.light.gridLine).toBe("rgba(18, 18, 18, 0.04)")
      expect(colors.light.divider).toBe("rgba(18, 18, 18, 0.06)")
    })
  })

  describe("dark mode colors", () => {
    it("defines background tokens", () => {
      expect(colors.dark.bgPrimary).toBe("#0D0F12")
      expect(colors.dark.bgElevated).toBe("#151820")
      expect(colors.dark.bgSubtle).toBe("#1A1D24")
    })

    it("defines text tokens", () => {
      expect(colors.dark.textPrimary).toBe("#E8E8E6")
      expect(colors.dark.textSecondary).toBe("#A5A5A3")
      expect(colors.dark.textTertiary).toBe("#6B6B68")
    })

    it("defines accent tokens", () => {
      expect(colors.dark.accent).toBe("#1C7A5A")
      expect(colors.dark.accentHover).toBe("#1F8F6A")
    })

    it("defines border tokens", () => {
      expect(colors.dark.borderPrimary).toBe("#252830")
    })

    it("defines semantic tokens", () => {
      expect(colors.dark.danger).toBe("#D45A5F")
      expect(colors.dark.warning).toBe("#D4A843")
    })

    it("defines grid and divider tokens", () => {
      expect(colors.dark.gridLine).toBe("rgba(255, 255, 255, 0.04)")
      expect(colors.dark.divider).toBe("rgba(255, 255, 255, 0.06)")
    })
  })

  describe("fonts", () => {
    it("defines font tokens", () => {
      expect(fonts.sans).toBe("var(--font-inter-tight)")
      expect(fonts.mono).toBe("var(--font-geist-mono)")
    })
  })

  describe("spacing", () => {
    it("uses 8px base scale", () => {
      expect(spacing[1]).toBe("8px")
      expect(spacing[2]).toBe("16px")
      expect(spacing[3]).toBe("24px")
      expect(spacing[5]).toBe("40px")
      expect(spacing[8]).toBe("64px")
      expect(spacing[20]).toBe("160px")
    })
  })
})
