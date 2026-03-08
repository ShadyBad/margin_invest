# Favicon Design

**Date:** 2026-03-08
**Status:** Approved

## Goal

Replace the default Vercel favicon with the Margin Invest logo mark so browsers display it in tabs, bookmarks, and mobile shortcuts.

## Approach

Static file-based using Next.js App Router file conventions. No `layout.tsx` changes needed — Next.js auto-generates `<head>` link tags from files in `src/app/`.

## Files

```
web/src/app/
├── favicon.ico        # 32×32 ICO — legacy browsers, Google search results
├── icon.svg           # Scalable — Chrome, Firefox, Edge (primary)
└── apple-icon.png     # 180×180 — iOS home screen, Safari tabs
```

## Icon Design

- **Shape:** Rounded square (`rx="3"` on 20×20 viewBox) filled with `#0A0F0D` (dark theme bg-primary)
- **Mark:** Chart polyline from existing `LogoIcon` component (`2,16 → 6,6 → 10,12 → 14,4 → 18,16`), stroked in `#1A7A5A` (accent green), `strokeWidth="1.5"`, `strokeLinecap="round"`, `strokeLinejoin="round"`
- **Border:** `0.5px` stroke on the rounded square in `rgba(26, 122, 90, 0.25)` for definition against dark browser chrome

The viewBox matches the existing `NavLogo` SVG so polyline coordinates are reused without transformation.

## Browser Coverage

| Browser | File Used |
|---|---|
| Chrome (desktop/Android) | `icon.svg` |
| Firefox | `icon.svg` |
| Edge | `icon.svg` |
| Safari (macOS tabs) | `favicon.ico` or `icon.svg` |
| Safari (iOS home screen) | `apple-icon.png` |
| Google search results | `favicon.ico` |

## Generation

- `icon.svg` — Hand-authored, source of truth
- `apple-icon.png` — One-time conversion from SVG at 180×180 (via `sharp` or CLI tool)
- `favicon.ico` — One-time conversion from SVG at 32×32

## Out of Scope

- PWA web manifest (`manifest.json` with 192×192 / 512×512 icons) — deferred until PWA support is needed
- Dynamic/theme-adaptive favicon (light vs dark mode) — unnecessary complexity for a fixed brand mark
