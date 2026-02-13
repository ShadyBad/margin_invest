import { describe, it, expect } from 'vitest'
import { colors, fonts } from '@/styles/tokens'

describe('Design Tokens', () => {
  it('defines all required color tokens', () => {
    expect(colors.bgPrimary).toBe('#0A0F1C')
    expect(colors.bgSecondary).toBe('#141B2D')
    expect(colors.gold).toBe('#D4A843')
    expect(colors.goldHover).toBe('#E8C468')
    expect(colors.bullish).toBe('#2D8B5E')
    expect(colors.bearish).toBe('#C74B50')
    expect(colors.textPrimary).toBe('#E8E4DD')
    expect(colors.textSecondary).toBe('#8B95A8')
    expect(colors.border).toBe('#1E2740')
  })

  it('has exactly 9 color tokens', () => {
    expect(Object.keys(colors)).toHaveLength(9)
  })

  it('defines font tokens referencing CSS custom properties', () => {
    expect(fonts.sans).toBe('var(--font-geist-sans)')
    expect(fonts.mono).toBe('var(--font-geist-mono)')
  })
})
