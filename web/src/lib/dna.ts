export const SECTOR_COLORS: Record<string, string> = {
  "Information Technology": "#1A3A5C",
  "Health Care": "#0E4F4F",
  "Financials": "#0F1E3A",
  "Energy": "#4A3018",
  "Consumer Discretionary": "#5C2A2A",
  "Industrials": "#2A2E33",
  "Materials": "#3A2A14",
  "Utilities": "#2A3A2A",
  "Real Estate": "#3A3228",
  "Communication Services": "#2A1E4A",
  "Consumer Staples": "#4A4038",
}

const DEFAULT_PALETTE = { base: "#0F0D0B", mid: "#1A5A3E", accent: "#1A7A5A" }

export interface DNAInput {
  sectorWeights: Record<string, number>
  tickerCount: number
  avgBeta: number
}

export interface DNAOutput {
  base: string
  mid: string
  accent: string
  density: number
  tempo: number
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase()}`
}

function blendColors(colors: { hex: string; weight: number }[]): string {
  if (colors.length === 0) return DEFAULT_PALETTE.base
  let r = 0,
    g = 0,
    b = 0
  for (const { hex, weight } of colors) {
    const [cr, cg, cb] = hexToRgb(hex)
    r += cr * weight
    g += cg * weight
    b += cb * weight
  }
  return rgbToHex(r, g, b)
}

export function blendSectorColors(
  sectorWeights: Record<string, number>,
): { base: string; mid: string; accent: string } {
  const entries = Object.entries(sectorWeights).filter(([sector]) => sector in SECTOR_COLORS)
  if (entries.length === 0) return DEFAULT_PALETTE

  const total = entries.reduce((sum, [, w]) => sum + w, 0)
  if (total === 0) return DEFAULT_PALETTE

  const weighted = entries.map(([sector, w]) => ({
    hex: SECTOR_COLORS[sector],
    weight: w / total,
  }))

  const base = blendColors(weighted)

  // Mid: lighten the blend by mixing with emerald
  const [br, bg, bb] = hexToRgb(base)
  const mid = rgbToHex(br * 0.5 + 0x1a * 0.5, bg * 0.5 + 0x5a * 0.5, bb * 0.5 + 0x3e * 0.5)

  // Accent: lighten further
  const accent = rgbToHex(
    br * 0.3 + 0x1a * 0.7,
    bg * 0.3 + 0x7a * 0.7,
    bb * 0.3 + 0x5a * 0.7,
  )

  return { base, mid, accent }
}

export function computeDNA(input: DNAInput): DNAOutput {
  const { sectorWeights, tickerCount, avgBeta } = input
  const palette = blendSectorColors(sectorWeights)

  // Density: 0-1 from ticker count (0 tickers = 0, 30+ = 1)
  const density = Math.min(1, Math.max(0, tickerCount / 30))

  // Tempo: 0.5-1.5 from avg beta (beta 0.5 = tempo 0.7, beta 1.5 = tempo 1.3)
  const tempo = Math.min(1.5, Math.max(0.5, 0.4 + avgBeta * 0.6))

  return { ...palette, density, tempo }
}
