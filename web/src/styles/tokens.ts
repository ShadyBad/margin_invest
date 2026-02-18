/**
 * Design system tokens for Margin Invest.
 *
 * Light/dark adaptive color system with warm off-white / charcoal-black
 * palette and muted emerald accent. Tokens mirror CSS custom properties
 * defined in globals.css via Tailwind @theme.
 *
 * For Tailwind utility classes, use the semantic names directly:
 *   bg-bg-primary, text-accent, border-border-primary, etc.
 */

export const colors = {
  light: {
    bgPrimary: "#F4F3EF",
    bgDeep: "#F4F3EF",
    bgElevated: "#FFFFFF",
    bgSubtle: "#ECEAE4",
    bgSurface: "#F7F4EE",
    textPrimary: "#121212",
    textSecondary: "#4A4A4A",
    textTertiary: "#8A8A86",
    accent: "#0E4F3A",
    accentHover: "#0B3E2E",
    accentGlow: "rgba(14, 79, 58, 0.15)",
    borderPrimary: "#D8D6D0",
    borderSubtle: "rgba(18, 18, 18, 0.04)",
    danger: "#C74B50",
    warning: "#B8860B",
    bullish: "#0E4F3A",
    bearish: "#C74B50",
    gridLine: "rgba(18, 18, 18, 0.04)",
    divider: "rgba(18, 18, 18, 0.06)",
    warmUnder: "#3A3228",
    caustic: "rgba(18, 18, 18, 0.08)",
  },
  dark: {
    bgPrimary: "#0D0F12",
    bgElevated: "#151820",
    bgSubtle: "#1A1D24",
    bgDeep: "#0F0D0B",
    bgSurface: "#1A1814",
    textPrimary: "#E8E8E6",
    textSecondary: "#A5A5A3",
    textTertiary: "#6B6B68",
    accent: "#1C7A5A",
    accentHover: "#1F8F6A",
    accentGlow: "rgba(14, 79, 58, 0.15)",
    borderPrimary: "#252830",
    borderSubtle: "rgba(255, 255, 255, 0.04)",
    danger: "#D45A5F",
    warning: "#D4A843",
    bullish: "#1A7A5A",
    bearish: "#D45A5F",
    gridLine: "rgba(255, 255, 255, 0.04)",
    divider: "rgba(255, 255, 255, 0.06)",
    warmUnder: "#2A1F14",
    caustic: "rgba(237, 233, 227, 0.12)",
  },
} as const

export type ColorMode = keyof typeof colors
export type ColorToken = keyof (typeof colors)["light"]

export const fonts = {
  sans: "var(--font-inter-tight)",
  mono: "var(--font-geist-mono)",
} as const

export type FontToken = keyof typeof fonts

export const spacing: Record<number, string> = {
  1: "8px",
  2: "16px",
  3: "24px",
  4: "32px",
  5: "40px",
  6: "48px",
  8: "64px",
  10: "80px",
  12: "96px",
  16: "128px",
  20: "160px",
} as const

export const motion = {
  easeOutExpo: "cubic-bezier(0.16, 1, 0.3, 1)",
  easeInOutSmooth: "cubic-bezier(0.45, 0, 0.55, 1)",
  easeOutBack: "cubic-bezier(0.22, 1, 0.36, 1)",
  durationMicro: "150ms",
  durationReveal: "600ms",
  durationTransition: "1000ms",
  durationAmbient: "10000ms",
  staggerBase: "80ms",
} as const

export const glass = {
  blur: "40px",
  saturation: "1.2",
  borderOpacity: "0.08",
  borderRadius: "16px",
  elevatedBlur: "60px",
  elevatedSaturation: "1.3",
} as const
