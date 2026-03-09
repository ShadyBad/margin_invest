# Favicon Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan one task at a time.

**Goal:** Add Margin Invest branded favicon files so browsers display the logo in tabs, bookmarks, and mobile shortcuts.

**Architecture:** Three static files in `web/src/app/` using Next.js App Router file-based metadata conventions. Next.js auto-generates head link tags. No code changes to layout.tsx. Icon is the existing chart polyline mark on a dark rounded-square background.

**Tech:** SVG, Next.js 16 file conventions, sharp (one-time PNG/ICO generation)

---

### Task 1: Create the SVG favicon

**Files:**
- Create: `web/src/app/icon.svg`

**Step 1: Write the SVG file**

Create `web/src/app/icon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 20 20">
  <rect x="0.25" y="0.25" width="19.5" height="19.5" rx="3" fill="#0A0F0D" stroke="rgba(26,122,90,0.25)" stroke-width="0.5"/>
  <polyline points="2,16 6,6 10,12 14,4 18,16" fill="none" stroke="#1A7A5A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

Design notes:
- viewBox of `0 0 20 20` matches existing LogoIcon in `web/src/components/nav/nav-logo.tsx`
- Polyline coordinates identical to nav logo
- rect inset by 0.25 to prevent border stroke clipping
- width/height of 32 is the intrinsic size but the SVG scales to any resolution

**Step 2: Verify it renders**

Run: `open web/src/app/icon.svg`

Confirm: dark rounded square with green chart line and subtle border.

**Step 3: Commit**

```
git add web/src/app/icon.svg
git commit -m "feat(web): add SVG favicon with Margin Invest logo mark"
```

---

### Task 2: Generate Apple touch icon and ICO via script

**Files:**
- Create: `web/scripts/generate-favicons.mjs`
- Create: `web/src/app/apple-icon.png` (generated)
- Create: `web/src/app/favicon.ico` (generated)

**Step 1: Install sharp as a dev dependency**

Run: `cd web && npm install --save-dev sharp`

**Step 2: Write the generation script**

Create `web/scripts/generate-favicons.mjs`:

```js
import sharp from "sharp";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const dir = dirname(fileURLToPath(import.meta.url));
const svgPath = resolve(dir, "../src/app/icon.svg");
const svg = readFileSync(svgPath);

// Apple touch icon at 180x180
await sharp(svg, { density: 450 })
  .resize(180, 180)
  .png()
  .toFile(resolve(dir, "../src/app/apple-icon.png"));

console.log("Done: apple-icon.png (180x180)");

// Favicon intermediate at 32x32
await sharp(svg, { density: 450 })
  .resize(32, 32)
  .png()
  .toFile(resolve(dir, "../src/app/favicon-32.png"));

console.log("Done: favicon-32.png (32x32)");
```

**Step 3: Run the script**

Run: `cd web && node scripts/generate-favicons.mjs`

Expected output:
```
Done: apple-icon.png (180x180)
Done: favicon-32.png (32x32)
```

**Step 4: Verify the PNG**

Run: `open web/src/app/apple-icon.png`

Confirm: 180x180 image with crisp dark rounded square and green chart line.

**Step 5: Convert 32x32 PNG to ICO and clean up**

Run: `cp web/src/app/favicon-32.png web/src/app/favicon.ico && rm web/src/app/favicon-32.png`

Modern browsers accept PNG-in-ICO. This is sufficient for legacy support and Google search results.

**Step 6: Commit**

```
git add web/src/app/apple-icon.png web/src/app/favicon.ico web/scripts/generate-favicons.mjs
git commit -m "feat(web): add apple-icon.png and favicon.ico with generation script"
```

---

### Task 3: Verify across browsers and run tests

**Files:**
- Verify: `web/src/app/icon.svg`, `web/src/app/apple-icon.png`, `web/src/app/favicon.ico`
- Verify: `web/src/app/layout.tsx` (no changes needed)

**Step 1: Start dev server**

Run: `cd web && npx next dev`

**Step 2: Check favicon in browser**

Open `http://localhost:3000` in Chrome:
- Browser tab should show the dark square with green chart line
- DevTools Elements tab should show auto-generated `<link rel="icon">` tags in the head
- Navigate to `http://localhost:3000/favicon.ico` directly to verify

Also check in Safari and Firefox if available.

**Step 3: Confirm no layout.tsx changes needed**

Verify `web/src/app/layout.tsx` has NO `icons` field in the metadata export. Next.js 16 infers all icon metadata from file conventions automatically.

**Step 4: Run the web test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass. No test changes needed (purely additive static files).

**Step 5: Run lint**

Run: `cd web && npx eslint --fix .`

Expected: Clean (SVG/PNG/ICO files are not linted).

**Step 6: Final commit if any cleanup needed**

```
git add -A web/src/app/
git commit -m "chore(web): favicon cleanup"
```
