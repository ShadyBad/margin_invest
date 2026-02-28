import { describe, it, expect } from "vitest"
import { colors, motion, glass } from "../tokens"

describe("design tokens", () => {
  it("exports evolved color palette with new depth tokens", () => {
    expect(colors.dark.bgDeep).toBe("#0F0D0B")
    expect(colors.dark.warmUnder).toBe("#2A1F14")
    expect(colors.dark.caustic).toBe("rgba(237, 233, 227, 0.12)")
    expect(colors.dark.accentGlow).toBe("rgba(14, 79, 58, 0.15)")
    expect(colors.light.bgSurface).toBe("#F7F4EE")
  })

  it("exports motion tokens with easing curves and durations", () => {
    expect(motion.easeOutExpo).toBe("cubic-bezier(0.16, 1, 0.3, 1)")
    expect(motion.easeInOutSmooth).toBe("cubic-bezier(0.45, 0, 0.55, 1)")
    expect(motion.easeOutBack).toBe("cubic-bezier(0.22, 1, 0.36, 1)")
    expect(motion.durationMicro).toBe("150ms")
    expect(motion.durationReveal).toBe("600ms")
    expect(motion.durationTransition).toBe("1000ms")
    expect(motion.staggerBase).toBe("80ms")
  })

  it("exports glass surface tokens", () => {
    expect(glass.blur).toBe("40px")
    expect(glass.saturation).toBe("1.2")
    expect(glass.borderOpacity).toBe("0.08")
    expect(glass.elevatedBlur).toBe("60px")
  })

  it("preserves existing semantic colors", () => {
    expect(colors.dark.bullish).toBeDefined()
    expect(colors.dark.bearish).toBeDefined()
    expect(colors.light.accent).toBe("#0E4F3A")
  })
})
