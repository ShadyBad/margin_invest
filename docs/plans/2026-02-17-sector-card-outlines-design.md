# Sector Card Outline Design

**Date:** 2026-02-17
**Branch:** feat/fluid-intelligence-redesign

## Objective

Visually differentiate candidate cards by GICS sector using a 2px left accent bar in muted earth tone colors. Replace the existing dark DNA sector colors with a unified palette that serves both card outlines and portfolio DNA computation.

## Decisions

- **Color source:** Single unified palette replacing existing `SECTOR_COLORS` in both `dna.ts` and `dna.py`
- **Styling layer:** Sector color replaces conviction-level border styling. Conviction retains glow, shadow, badge, and score size.
- **Border style:** 2px left accent bar (finance dashboard convention)
- **Color tone:** Muted earth tones (desaturated, warm-leaning, 35-55% saturation)
- **Sector label:** No text on card. Color-only indicator.
- **Architecture:** CSS custom properties in `globals.css` with TypeScript lookup map (Approach A)

## Sector Color Palette

| Sector | CSS Variable | Light Mode | Dark Mode |
|--------|-------------|-----------|-----------|
| Information Technology | `--color-sector-tech` | `#5B7A8A` | `#7A9AAA` |
| Health Care | `--color-sector-healthcare` | `#4F7A6B` | `#6A9A8A` |
| Financials | `--color-sector-financials` | `#4A5E7A` | `#6A7E9A` |
| Consumer Discretionary | `--color-sector-consumer-disc` | `#8A6254` | `#AA8274` |
| Consumer Staples | `--color-sector-consumer-staples` | `#7A7250` | `#9A9270` |
| Energy | `--color-sector-energy` | `#8A6E3A` | `#AA8E5A` |
| Industrials | `--color-sector-industrials` | `#6B6E72` | `#8B8E92` |
| Materials | `--color-sector-materials` | `#7A6050` | `#9A8070` |
| Real Estate | `--color-sector-real-estate` | `#7A7060` | `#9A9080` |
| Utilities | `--color-sector-utilities` | `#5A7A5A` | `#7A9A7A` |
| Communication Services | `--color-sector-comms` | `#6E5A7A` | `#8E7A9A` |

**Design rationale:**
- 35-55% saturation: distinguishable without being loud
- Light variants: 4:1+ contrast against `#FEFDFB` card backgrounds
- Dark variants: 4:1+ contrast against `#1A1A18` card backgrounds
- Hue spacing allows at-a-glance differentiation across a grid
- Warm-leaning tones match the existing off-white/charcoal/emerald palette

## Architecture

### CSS Variables (globals.css)

Add 11 sector color variables to `:root` and `.dark` blocks alongside existing design tokens.

```css
:root {
  --color-sector-tech: #5B7A8A;
  --color-sector-healthcare: #4F7A6B;
  --color-sector-financials: #4A5E7A;
  --color-sector-consumer-disc: #8A6254;
  --color-sector-consumer-staples: #7A7250;
  --color-sector-energy: #8A6E3A;
  --color-sector-industrials: #6B6E72;
  --color-sector-materials: #7A6050;
  --color-sector-real-estate: #7A7060;
  --color-sector-utilities: #5A7A5A;
  --color-sector-comms: #6E5A7A;
}

.dark {
  --color-sector-tech: #7A9AAA;
  --color-sector-healthcare: #6A9A8A;
  --color-sector-financials: #6A7E9A;
  --color-sector-consumer-disc: #AA8274;
  --color-sector-consumer-staples: #9A9270;
  --color-sector-energy: #AA8E5A;
  --color-sector-industrials: #8B8E92;
  --color-sector-materials: #9A8070;
  --color-sector-real-estate: #9A9080;
  --color-sector-utilities: #7A9A7A;
  --color-sector-comms: #8E7A9A;
}
```

### TypeScript Lookup (new file: web/src/lib/sector-colors.ts)

```ts
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
  return SECTOR_BORDER_COLOR[sector ?? ""] ?? "var(--color-border-primary)";
}
```

Fallback to `border-primary` for cards without sector data.

## API Changes

Add `sector` to the `PickSummary` response so cards receive sector data:

1. **`api/src/margin_api/schemas/dashboard.py`** — Add `sector: str | None = None` to `PickSummary`
2. **Route handler** — Join on `Asset` table to pull `asset.sector` when building the response
3. **`web/src/lib/api/types.ts`** — Add `sector?: string | null` to frontend `PickSummary` type

No new endpoints. No schema migrations. `Asset.sector` is already populated by the data pipeline.

## Card Component Changes

**File:** `web/src/components/dashboard/stock-card.tsx`

### What changes:
- Import `getSectorColor` from `sector-colors.ts`
- All cards get `border-l-2` with `style={{ borderLeftColor: getSectorColor(pick.sector) }}`
- Remove conviction-based border color logic (`border-accent/30`, `border-l-accent`)

### What stays:
- Exceptional: top accent bar (`h-[2px] bg-accent`), glow shadow, radial gradient overlay
- High: elevated shadow
- Score size, conviction badge, shadow intensity — all unchanged
- Default `border-border-primary` on top/right/bottom edges

## DNA Integration

Replace `SECTOR_COLORS` in both files with the new light-mode hex values:

- **`web/src/lib/dna.ts`** — Update `SECTOR_COLORS` record
- **`api/src/margin_api/routes/dna.py`** — Update `SECTOR_COLORS` dict

Blending functions (`blendSectorColors`, `computeDNA`) remain unchanged. They operate on the new input colors.

## Files Modified

| File | Change |
|------|--------|
| `web/src/app/globals.css` | Add 11 sector CSS variables (light + dark) |
| `web/src/lib/sector-colors.ts` | New file: sector → CSS variable map + helper |
| `web/src/lib/dna.ts` | Replace `SECTOR_COLORS` hex values |
| `web/src/lib/api/types.ts` | Add `sector` to `PickSummary` type |
| `web/src/components/dashboard/stock-card.tsx` | Sector left bar, remove conviction border logic |
| `api/src/margin_api/schemas/dashboard.py` | Add `sector` to `PickSummary` |
| `api/src/margin_api/routes/dashboard.py` (or equivalent) | Join Asset.sector into response |
| `api/src/margin_api/routes/dna.py` | Replace `SECTOR_COLORS` hex values |
