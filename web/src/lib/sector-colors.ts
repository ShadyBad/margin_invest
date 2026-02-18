/**
 * Sector-to-CSS-variable mapping for card left-bar coloring.
 * Colors are defined in globals.css as --color-sector-* variables.
 */
export const SECTOR_BORDER_COLOR: Record<string, string> = {
  "Information Technology": "var(--color-sector-tech)",
  "Health Care": "var(--color-sector-healthcare)",
  "Financials": "var(--color-sector-financials)",
  "Consumer Discretionary": "var(--color-sector-consumer-disc)",
  "Consumer Staples": "var(--color-sector-consumer-staples)",
  "Energy": "var(--color-sector-energy)",
  "Industrials": "var(--color-sector-industrials)",
  "Materials": "var(--color-sector-materials)",
  "Real Estate": "var(--color-sector-real-estate)",
  "Utilities": "var(--color-sector-utilities)",
  "Communication Services": "var(--color-sector-comms)",
}

export function getSectorColor(sector: string | null | undefined): string {
  return SECTOR_BORDER_COLOR[sector ?? ""] ?? "var(--color-border-primary)"
}
