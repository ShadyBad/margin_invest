/**
 * Design system tokens for Margin Invest.
 *
 * These constants mirror the CSS custom properties defined in globals.css
 * and are intended for programmatic use (e.g. charts, canvas, inline styles).
 *
 * For Tailwind utility classes, use the token names directly:
 *   bg-bg-primary, text-gold, border-border, etc.
 */

export const colors = {
  bgPrimary: '#0A0F1C',
  bgSecondary: '#141B2D',
  gold: '#D4A843',
  goldHover: '#E8C468',
  bullish: '#2D8B5E',
  bearish: '#C74B50',
  textPrimary: '#E8E4DD',
  textSecondary: '#8B95A8',
  border: '#1E2740',
} as const

export type ColorToken = keyof typeof colors

export const fonts = {
  sans: 'var(--font-geist-sans)',
  mono: 'var(--font-geist-mono)',
} as const

export type FontToken = keyof typeof fonts
