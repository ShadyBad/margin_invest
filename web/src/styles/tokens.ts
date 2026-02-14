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
    bgElevated: "#FFFFFF",
    bgSubtle: "#ECEAE4",
    textPrimary: "#121212",
    textSecondary: "#5C5C5C",
    textTertiary: "#8A8A86",
    accent: "#0E4F3A",
    accentHover: "#0B3E2E",
    borderPrimary: "#D8D6D0",
    danger: "#C74B50",
    warning: "#B8860B",
    bullish: "#0E4F3A",
    bearish: "#C74B50",
  },
  dark: {
    bgPrimary: "#0D0F12",
    bgElevated: "#151820",
    bgSubtle: "#1A1D24",
    textPrimary: "#E8E8E6",
    textSecondary: "#9B9B98",
    textTertiary: "#6B6B68",
    accent: "#1A7A5A",
    accentHover: "#1F8F6A",
    borderPrimary: "#252830",
    danger: "#D45A5F",
    warning: "#D4A843",
    bullish: "#1A7A5A",
    bearish: "#D45A5F",
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
