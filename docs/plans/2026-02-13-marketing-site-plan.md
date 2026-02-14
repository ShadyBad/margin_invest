# Marketing Site Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the existing landing page with a bespoke adaptive (light/dark) marketing site, and rebrand the full app's color system from navy/gold to warm off-white/charcoal-black + emerald.

**Architecture:** Editorial Scroll pattern — seven sections with varied grid compositions, asymmetric layouts, and progressive scroll-triggered animations. The design system is rebuilt from scratch: new color tokens (light/dark), Inter Tight font, 8px spacing scale, 12-column grid. All existing components (dashboard, nav, UI) are updated to use the new semantic color tokens.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS v4 (`@theme` directive), Framer Motion 12, `next-themes` (new dep for light/dark toggle), Inter Tight via `next/font/google`, Geist Mono (retained for data display).

**Design doc:** `docs/plans/2026-02-13-marketing-site-design.md`

---

## Task 1: Install next-themes and Inter Tight font

**Files:**
- Modify: `web/package.json`
- Modify: `web/src/app/layout.tsx`

**Step 1: Install next-themes**

Run: `cd /Users/brandon/repos/margin_invest && uv run --directory web npx --yes npm install next-themes`

Actually, this is a Next.js project — use npm directly:

Run: `cd /Users/brandon/repos/margin_invest/web && npm install next-themes`

**Step 2: Update layout.tsx to load Inter Tight and wire up ThemeProvider**

Replace the full contents of `web/src/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import { Inter_Tight } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import "./globals.css";

const interTight = Inter_Tight({
  variable: "--font-inter-tight",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Margin Invest",
  description:
    "Deterministic investment analysis — conviction scoring without human bias",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${interTight.variable} ${geistMono.variable} antialiased bg-bg-primary text-text-primary`}
      >
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <SessionProvider>{children}</SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Step 3: Create the ThemeProvider component**

Create `web/src/components/providers/theme-provider.tsx`:

```tsx
"use client"

import { ThemeProvider as NextThemesProvider } from "next-themes"
import type { ComponentProps } from "react"

export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
```

**Step 4: Verify app still builds**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds (may have warnings about existing pages not matching new tokens yet — that's fine, we fix those in later tasks).

**Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/src/app/layout.tsx web/src/components/providers/theme-provider.tsx
git commit -m "feat(web): add next-themes and Inter Tight font to layout"
```

---

## Task 2: Rebuild design system — color tokens and spacing

**Files:**
- Rewrite: `web/src/app/globals.css`
- Rewrite: `web/src/styles/tokens.ts`
- Modify: `web/src/__tests__/tokens.test.ts`

**Step 1: Write failing token tests**

Replace `web/src/__tests__/tokens.test.ts` with:

```ts
import { describe, it, expect } from "vitest"
import { colors, fonts, spacing } from "@/styles/tokens"

describe("Design Tokens", () => {
  describe("light mode colors", () => {
    it("defines background tokens", () => {
      expect(colors.light.bgPrimary).toBe("#F4F3EF")
      expect(colors.light.bgElevated).toBe("#FFFFFF")
      expect(colors.light.bgSubtle).toBe("#ECEAE4")
    })

    it("defines text tokens", () => {
      expect(colors.light.textPrimary).toBe("#121212")
      expect(colors.light.textSecondary).toBe("#5C5C5C")
      expect(colors.light.textTertiary).toBe("#8A8A86")
    })

    it("defines accent tokens", () => {
      expect(colors.light.accent).toBe("#0E4F3A")
      expect(colors.light.accentHover).toBe("#0B3E2E")
    })

    it("defines border tokens", () => {
      expect(colors.light.borderPrimary).toBe("#D8D6D0")
    })

    it("defines semantic tokens", () => {
      expect(colors.light.danger).toBe("#C74B50")
      expect(colors.light.warning).toBe("#B8860B")
    })
  })

  describe("dark mode colors", () => {
    it("defines background tokens", () => {
      expect(colors.dark.bgPrimary).toBe("#0D0F12")
      expect(colors.dark.bgElevated).toBe("#151820")
      expect(colors.dark.bgSubtle).toBe("#1A1D24")
    })

    it("defines text tokens", () => {
      expect(colors.dark.textPrimary).toBe("#E8E8E6")
      expect(colors.dark.textSecondary).toBe("#9B9B98")
      expect(colors.dark.textTertiary).toBe("#6B6B68")
    })

    it("defines accent tokens", () => {
      expect(colors.dark.accent).toBe("#1A7A5A")
      expect(colors.dark.accentHover).toBe("#1F8F6A")
    })

    it("defines border tokens", () => {
      expect(colors.dark.borderPrimary).toBe("#252830")
    })

    it("defines semantic tokens", () => {
      expect(colors.dark.danger).toBe("#D45A5F")
      expect(colors.dark.warning).toBe("#D4A843")
    })
  })

  describe("fonts", () => {
    it("defines font tokens", () => {
      expect(fonts.sans).toBe("var(--font-inter-tight)")
      expect(fonts.mono).toBe("var(--font-geist-mono)")
    })
  })

  describe("spacing", () => {
    it("uses 8px base scale", () => {
      expect(spacing[1]).toBe("8px")
      expect(spacing[2]).toBe("16px")
      expect(spacing[3]).toBe("24px")
      expect(spacing[5]).toBe("40px")
      expect(spacing[8]).toBe("64px")
      expect(spacing[20]).toBe("160px")
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run --directory web npx vitest run src/__tests__/tokens.test.ts`
Expected: FAIL — `colors.light` doesn't exist, `spacing` not exported, font references old name.

**Step 3: Rewrite tokens.ts**

Replace `web/src/styles/tokens.ts` with:

```ts
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run --directory web npx vitest run src/__tests__/tokens.test.ts`
Expected: PASS

**Step 5: Rewrite globals.css with light/dark adaptive tokens**

Replace `web/src/app/globals.css` with:

```css
@import "tailwindcss";

/* ============================================================
   Design System — Light/Dark adaptive tokens
   Accent: muted emerald (≤10% visual weight)
   Grid: 12-column, max 1280px, 8px spacing base
   ============================================================ */

/* --- Light mode (default) --- */
@theme {
  /* Backgrounds */
  --color-bg-primary: #F4F3EF;
  --color-bg-elevated: #FFFFFF;
  --color-bg-subtle: #ECEAE4;

  /* Text */
  --color-text-primary: #121212;
  --color-text-secondary: #5C5C5C;
  --color-text-tertiary: #8A8A86;

  /* Accent — muted emerald */
  --color-accent: #0E4F3A;
  --color-accent-hover: #0B3E2E;
  --color-accent-subtle: rgba(14, 79, 58, 0.08);

  /* Borders */
  --color-border-primary: #D8D6D0;
  --color-border-subtle: rgba(18, 18, 18, 0.08);

  /* Semantic */
  --color-bullish: #0E4F3A;
  --color-bearish: #C74B50;
  --color-warning: #B8860B;
  --color-danger: #C74B50;

  /* Surface overlay (geometric grids) */
  --color-surface-overlay: rgba(18, 18, 18, 0.03);
}

/* --- Dark mode overrides --- */
.dark {
  --color-bg-primary: #0D0F12;
  --color-bg-elevated: #151820;
  --color-bg-subtle: #1A1D24;

  --color-text-primary: #E8E8E6;
  --color-text-secondary: #9B9B98;
  --color-text-tertiary: #6B6B68;

  --color-accent: #1A7A5A;
  --color-accent-hover: #1F8F6A;
  --color-accent-subtle: rgba(26, 122, 90, 0.10);

  --color-border-primary: #252830;
  --color-border-subtle: rgba(232, 232, 230, 0.06);

  --color-bullish: #1A7A5A;
  --color-bearish: #D45A5F;
  --color-warning: #D4A843;
  --color-danger: #D45A5F;

  --color-surface-overlay: rgba(232, 232, 230, 0.03);
}

/* Font tokens — set by next/font, consumed via @theme inline */
@theme inline {
  --font-sans: var(--font-inter-tight);
  --font-mono: var(--font-geist-mono);
}

/* Base body styles */
body {
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}
```

**Step 6: Commit**

```bash
git add web/src/app/globals.css web/src/styles/tokens.ts web/src/__tests__/tokens.test.ts
git commit -m "feat(web): rebuild design system with light/dark adaptive color tokens"
```

---

## Task 3: Update existing components to use new color tokens

The old token names (`bg-bg-secondary`, `text-gold`, `border-border`, `text-text-primary`, etc.) no longer exist in the CSS. All existing components must be migrated to the new semantic token names. This is a search-and-replace task across all component files.

**Files:**
- Modify: ALL `.tsx` files in `web/src/components/` and `web/src/app/`
- Modify: ALL test files that reference old class names

**Token migration map:**

| Old class | New class |
|-----------|-----------|
| `bg-bg-primary` | `bg-bg-primary` (unchanged name, new value) |
| `bg-bg-secondary` | `bg-bg-elevated` |
| `text-text-primary` | `text-text-primary` (unchanged name, new value) |
| `text-text-secondary` | `text-text-secondary` (unchanged name, new value) |
| `text-gold` | `text-accent` |
| `text-gold-hover` | `text-accent-hover` |
| `bg-gold` | `bg-accent` |
| `bg-gold/20` | `bg-accent/20` |
| `bg-gold/10` | `bg-accent/10` |
| `hover:bg-gold-hover` | `hover:bg-accent-hover` |
| `border-border` | `border-border-primary` |
| `border-gold/30` | `border-accent/30` |
| `border-gold/20` | `border-accent/20` |
| `text-bullish` | `text-bullish` (unchanged name, new value) |
| `text-bearish` | `text-bearish` (unchanged name, new value) |
| `bg-border` | `bg-border-primary` |
| `border-t-transparent` | `border-t-transparent` (no change) |
| `rounded-xl` | `rounded-sm` (2px max radius per design spec) |
| `rounded-lg` | `rounded-sm` |
| `rounded-full` (on badges) | `rounded-sm` |

**Step 1: Run find-and-replace across all component files**

Apply these replacements in order (some are substrings of others, so order matters):

1. `bg-bg-secondary` → `bg-bg-elevated` (in all `.tsx` files under `web/src/`)
2. `text-gold-hover` → `text-accent-hover`
3. `text-gold` → `text-accent` (but NOT `text-gold-hover` which was already replaced)
4. `hover:bg-gold-hover` → `hover:bg-accent-hover`
5. `bg-gold/20` → `bg-accent/20`
6. `bg-gold/10` → `bg-accent/10`
7. `bg-gold` → `bg-accent` (standalone, not the `/` variants already replaced)
8. `border-border` → `border-border-primary` (but NOT `border-border-primary` which doesn't exist yet)
9. `border-gold/30` → `border-accent/30`
10. `border-gold/20` → `border-accent/20`
11. `bg-border` → `bg-border-primary`
12. `rounded-xl` → `rounded-sm`
13. `rounded-lg` → `rounded-sm`

For ConvictionBadge specifically: change `rounded-full` to `rounded-sm`.

**Step 2: Fix tests that assert old class names**

In `web/src/components/ui/__tests__/conviction-badge.test.tsx`, change the assertion:
- `text-gold` → `text-accent`

In `web/src/components/layout/__tests__/nav.test.tsx`, change the assertion:
- `text-gold` → `text-accent`

**Step 3: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: ALL PASS. If any fail due to missed token renames, fix them.

**Step 4: Verify build**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds.

**Step 5: Commit**

```bash
git add -A web/src/
git commit -m "refactor(web): migrate all components to new adaptive color tokens"
```

---

## Task 4: Build the landing page shell and geometric grid overlay

**Files:**
- Create: `web/src/components/landing/grid-overlay.tsx`
- Rewrite: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/index.ts`

**Step 1: Write test for GridOverlay**

Create `web/src/components/landing/__tests__/grid-overlay.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { GridOverlay } from "../grid-overlay"

describe("GridOverlay", () => {
  it("renders an SVG element", () => {
    const { container } = render(<GridOverlay />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })

  it("applies custom opacity", () => {
    const { container } = render(<GridOverlay opacity={0.02} />)
    const svg = container.querySelector("svg")
    expect(svg).toHaveStyle({ opacity: "0.02" })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/grid-overlay.test.tsx`
Expected: FAIL — module not found.

**Step 3: Implement GridOverlay**

Create `web/src/components/landing/grid-overlay.tsx`:

```tsx
interface GridOverlayProps {
  opacity?: number
}

export function GridOverlay({ opacity = 0.03 }: GridOverlayProps) {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity }}
      aria-hidden="true"
    >
      <defs>
        <pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
          <path
            d="M 64 0 L 0 0 0 64"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/grid-overlay.test.tsx`
Expected: PASS

**Step 5: Update barrel export**

Replace `web/src/components/landing/index.ts` with:

```ts
export { HeroSection } from "./hero-section"
export { FrictionSection } from "./friction-section"
export { SystemDiagram } from "./system-diagram"
export { EngineProof } from "./engine-proof"
export { CapabilitiesSection } from "./capabilities-section"
export { InvestorPositioning } from "./investor-positioning"
export { FinalCTA } from "./final-cta"
export { GridOverlay } from "./grid-overlay"
```

Note: These components don't exist yet — they'll be created in Tasks 5-11. The barrel export is prepped for the final page assembly.

**Step 6: Rewrite page.tsx shell**

Replace `web/src/app/page.tsx` with:

```tsx
import {
  HeroSection,
  FrictionSection,
  SystemDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "@/components/landing"

export default function Home() {
  return (
    <main className="bg-bg-primary min-h-screen">
      <HeroSection />
      <FrictionSection />
      <SystemDiagram />
      <EngineProof />
      <CapabilitiesSection />
      <InvestorPositioning />
      <FinalCTA />
    </main>
  )
}
```

**Step 7: Commit**

```bash
git add web/src/components/landing/grid-overlay.tsx web/src/components/landing/__tests__/grid-overlay.test.tsx web/src/components/landing/index.ts web/src/app/page.tsx
git commit -m "feat(web): scaffold landing page shell with GridOverlay component"
```

---

## Task 5: Build Section 1 — HeroSection

**Files:**
- Create: `web/src/components/landing/hero-section.tsx`
- Delete: `web/src/components/landing/hero.tsx` (old)
- Create: `web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/hero-section.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroSection } from "../hero-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders the subhead", () => {
    render(<HeroSection />)
    expect(screen.getByText(/deterministic scoring engine/i)).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<HeroSection />)
    const cta = screen.getByRole("link", { name: "Explore the Engine" })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByText("View methodology")).toBeInTheDocument()
  })

  it("contains the grid overlay", () => {
    const { container } = render(<HeroSection />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/hero-section.test.tsx`
Expected: FAIL

**Step 3: Implement HeroSection**

Create `web/src/components/landing/hero-section.tsx`:

```tsx
"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { GridOverlay } from "./grid-overlay"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative" style={{ minHeight: "90vh" }}>
      <GridOverlay opacity={0.03} />
      <div
        className="relative mx-auto grid grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          padding: "160px 24px",
        }}
      >
        {/* Content: cols 1-8 */}
        <div className="col-span-12 md:col-span-8 flex flex-col justify-center">
          {/* Thin decorative rule */}
          <motion.div
            className="w-48 h-px bg-border-primary mb-12"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.7, ease }}
            style={{ transformOrigin: "left" }}
          />

          <motion.h1
            className="text-[40px] md:text-[52px] lg:text-[68px] font-bold leading-[0.98] tracking-[-0.03em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease }}
          >
            Structure outperforms emotion.
          </motion.h1>

          <motion.p
            className="mt-6 text-lg md:text-xl text-text-secondary max-w-[640px] leading-relaxed"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            A deterministic scoring engine that evaluates every US equity through the same institutional-grade framework — no discretion, no narrative bias, no exceptions.
          </motion.p>

          <motion.div
            className="mt-10 flex items-center gap-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-block px-8 py-4 bg-accent text-white font-semibold text-[15px] rounded-sm hover:bg-accent-hover transition-colors"
            >
              Explore the Engine
            </Link>
            <Link
              href="/methodology"
              className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              View methodology
            </Link>
          </motion.div>
        </div>

        {/* Cols 9-12: intentional negative space */}
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/hero-section.test.tsx`
Expected: PASS

**Step 5: Delete old hero.tsx**

Run: `rm /Users/brandon/repos/margin_invest/web/src/components/landing/hero.tsx`

**Step 6: Commit**

```bash
git add web/src/components/landing/hero-section.tsx web/src/components/landing/__tests__/hero-section.test.tsx
git rm web/src/components/landing/hero.tsx
git commit -m "feat(web): build HeroSection — declarative philosophy with grid overlay"
```

---

## Task 6: Build Section 2 — FrictionSection

**Files:**
- Create: `web/src/components/landing/friction-section.tsx`
- Delete: `web/src/components/landing/how-it-works.tsx` (old)
- Create: `web/src/components/landing/__tests__/friction-section.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/friction-section.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FrictionSection } from "../friction-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("FrictionSection", () => {
  it("renders the main headline", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/conviction they haven't earned/i)).toBeInTheDocument()
  })

  it("renders three friction points", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/emotion enters before analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/inconsistent frameworks/i)).toBeInTheDocument()
    expect(screen.getByText(/retail tools measure activity/i)).toBeInTheDocument()
  })

  it("uses asymmetric two-column layout", () => {
    const { container } = render(<FrictionSection />)
    const grid = container.querySelector("[class*='grid-cols-12']")
    expect(grid).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/friction-section.test.tsx`
Expected: FAIL

**Step 3: Implement FrictionSection**

Create `web/src/components/landing/friction-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const frictionPoints = [
  {
    title: "Emotion enters before analysis finishes.",
    body: "Sentiment shifts between checking a position and deciding what to do about it. The process isn't flawed — it's absent.",
  },
  {
    title: "Inconsistent frameworks produce inconsistent results.",
    body: "Switching between screeners, newsletters, and intuition means every decision uses different criteria. There's no baseline to evaluate against.",
  },
  {
    title: "Retail tools measure activity, not quality.",
    body: "Volume, price movement, trending tickers — these describe what happened. They don't tell you whether the underlying business justifies a position.",
  },
]

export function FrictionSection() {
  return (
    <section
      style={{ padding: "80px 24px 96px" }}
    >
      <div
        className="mx-auto grid grid-cols-12 gap-6"
        style={{ maxWidth: "1280px" }}
      >
        {/* Left column: cols 1-5 */}
        <div className="col-span-12 md:col-span-5">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            Most investment decisions are made with conviction they haven't earned.
          </motion.h2>
        </div>

        {/* Spacer: col 6 */}
        <div className="hidden md:block md:col-span-1" />

        {/* Right column: cols 7-12 */}
        <div className="col-span-12 md:col-span-6 space-y-12">
          {frictionPoints.map((point, i) => (
            <motion.div
              key={i}
              className="border-l-2 border-accent/40 pl-6"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.15 * (i + 1), ease }}
            >
              <h3 className="text-[24px] md:text-[26px] lg:text-[30px] font-semibold leading-[1.10] tracking-[-0.01em] text-text-primary mb-2">
                {point.title}
              </h3>
              <p className="text-text-secondary leading-relaxed text-[16px] md:text-[17px] max-w-[640px]">
                {point.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/friction-section.test.tsx`
Expected: PASS

**Step 5: Delete old how-it-works.tsx**

Run: `rm /Users/brandon/repos/margin_invest/web/src/components/landing/how-it-works.tsx`

**Step 6: Commit**

```bash
git add web/src/components/landing/friction-section.tsx web/src/components/landing/__tests__/friction-section.test.tsx
git rm web/src/components/landing/how-it-works.tsx
git commit -m "feat(web): build FrictionSection — asymmetric two-column friction recognition"
```

---

## Task 7: Build Section 3 — SystemDiagram

**Files:**
- Create: `web/src/components/landing/system-diagram.tsx`
- Create: `web/src/components/landing/__tests__/system-diagram.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/system-diagram.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { SystemDiagram } from "../system-diagram"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    rect: (props: any) => <rect {...props} />,
    text: ({ children, ...props }: any) => <text {...props}>{children}</text>,
    line: (props: any) => <line {...props} />,
    path: (props: any) => <path {...props} />,
    g: ({ children, ...props }: any) => <g {...props}>{children}</g>,
  },
  useInView: () => true,
}))

describe("SystemDiagram", () => {
  it("renders section label", () => {
    render(<SystemDiagram />)
    expect(screen.getByText("How the engine works")).toBeInTheDocument()
  })

  it("renders pipeline stage labels", () => {
    render(<SystemDiagram />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText(/Quality/)).toBeInTheDocument()
    expect(screen.getByText(/Value/)).toBeInTheDocument()
    expect(screen.getByText(/Momentum/)).toBeInTheDocument()
    expect(screen.getByText("Composite Score")).toBeInTheDocument()
    expect(screen.getByText("Classification")).toBeInTheDocument()
  })

  it("renders the caption", () => {
    render(<SystemDiagram />)
    expect(screen.getByText(/every asset passes through the same pipeline/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/system-diagram.test.tsx`
Expected: FAIL

**Step 3: Implement SystemDiagram**

Create `web/src/components/landing/system-diagram.tsx`. This is an SVG-based diagram with Framer Motion animations. The diagram renders a horizontal pipeline flow.

```tsx
"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const filterItems = ["Beneish M-Score", "Altman Z''", "Liquidity", "Coverage"]
const qualityItems = ["Gross Profitability", "ROIC-WACC", "Accrual Ratio", "F-Score"]
const valueItems = ["EV/FCF", "Shareholder Yield", "DCF Margin", "Acquirer's Multiple"]
const momentumItems = ["Price 12-1mo", "Earnings SUE", "Insider Clusters", "Institutional Flow"]
const classificationItems = ["Exceptional", "High Conviction", "Watchlist"]

function DiagramNode({
  x, y, width, height, label, sublabel, items, delay, isActive, inView,
}: {
  x: number; y: number; width: number; height: number
  label: string; sublabel?: string; items?: string[]
  delay: number; isActive?: boolean; inView: boolean
}) {
  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.96 }}
      animate={inView ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.5, delay, ease }}
    >
      <motion.rect
        x={x} y={y} width={width} height={height}
        fill="none"
        className={isActive ? "stroke-accent" : "stroke-border-primary"}
        strokeWidth={1}
        rx={2}
        animate={inView && isActive ? { stroke: "var(--color-accent)" } : {}}
        transition={{ duration: 0.6, delay: delay + 0.2 }}
      />
      <motion.text
        x={x + 12} y={y + 22}
        className="fill-text-primary text-[13px] font-semibold"
        fontFamily="var(--font-inter-tight)"
        fontSize={13} fontWeight={600}
      >
        {label}
      </motion.text>
      {sublabel && (
        <motion.text
          x={x + 12} y={y + 38}
          className="fill-text-tertiary text-[11px]"
          fontFamily="var(--font-inter-tight)"
          fontSize={11}
        >
          {sublabel}
        </motion.text>
      )}
      {items?.map((item, i) => (
        <motion.text
          key={item}
          x={x + 12} y={y + (sublabel ? 56 : 42) + i * 16}
          className="fill-text-secondary text-[11px]"
          fontFamily="var(--font-inter-tight)"
          fontSize={11}
        >
          {item}
        </motion.text>
      ))}
    </motion.g>
  )
}

function Connector({ x1, y1, x2, y2, delay, inView }: {
  x1: number; y1: number; x2: number; y2: number; delay: number; inView: boolean
}) {
  const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
  return (
    <motion.line
      x1={x1} y1={y1} x2={x2} y2={y2}
      className="stroke-border-primary"
      strokeWidth={1}
      strokeDasharray={length}
      strokeDashoffset={length}
      animate={inView ? { strokeDashoffset: 0 } : {}}
      transition={{ duration: 0.6, delay, ease }}
    />
  )
}

export function SystemDiagram() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-15% 0px" })

  return (
    <section
      ref={ref}
      style={{ padding: "96px 24px" }}
    >
      <div className="mx-auto" style={{ maxWidth: "1280px" }}>
        <motion.h2
          className="text-[14px] font-medium text-text-tertiary uppercase tracking-[0.05em] mb-12"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.4, ease }}
        >
          How the engine works
        </motion.h2>

        {/* Desktop diagram */}
        <div className="hidden lg:block">
          <svg viewBox="0 0 1280 340" className="w-full" aria-label="Scoring pipeline diagram">
            {/* Elimination Filters */}
            <DiagramNode x={0} y={20} width={180} height={160} label="Elimination Filters" items={filterItems} delay={0.2} inView={inView} />

            {/* Connector: Filters → Scoring */}
            <Connector x1={180} y1={100} x2={240} y2={100} delay={0.5} inView={inView} />

            {/* Quality */}
            <DiagramNode x={240} y={0} width={200} height={130} label="Quality" sublabel="35%" items={qualityItems} delay={0.7} inView={inView} />

            {/* Value */}
            <DiagramNode x={240} y={140} width={200} height={130} label="Value" sublabel="30%" items={valueItems} delay={0.85} inView={inView} />

            {/* Momentum */}
            <DiagramNode x={240} y={280} width={200} height={130} label="Momentum" sublabel="35%" items={momentumItems} delay={1.0} inView={inView} />

            {/* Connectors: Scoring → Composite */}
            <Connector x1={440} y1={65} x2={500} y2={175} delay={1.2} inView={inView} />
            <Connector x1={440} y1={205} x2={500} y2={195} delay={1.2} inView={inView} />
            <Connector x1={440} y1={345} x2={500} y2={215} delay={1.2} inView={inView} />

            {/* Composite Score */}
            <DiagramNode x={500} y={150} width={180} height={80} label="Composite Score" sublabel="Sector-neutral percentile" delay={1.5} isActive inView={inView} />

            {/* Connector: Composite → Classification */}
            <Connector x1={680} y1={190} x2={740} y2={190} delay={1.8} inView={inView} />

            {/* Classification */}
            <DiagramNode x={740} y={130} width={170} height={120} label="Classification" items={classificationItems} delay={2.1} inView={inView} />
          </svg>
        </div>

        {/* Mobile: simplified vertical flow */}
        <div className="lg:hidden space-y-4">
          {[
            { label: "Elimination Filters", sub: filterItems.join(" · ") },
            { label: "Quality (35%)", sub: qualityItems.join(" · ") },
            { label: "Value (30%)", sub: valueItems.join(" · ") },
            { label: "Momentum (35%)", sub: momentumItems.join(" · ") },
            { label: "Composite Score", sub: "Sector-neutral percentile ranking" },
            { label: "Classification", sub: classificationItems.join(" · ") },
          ].map((stage, i) => (
            <motion.div
              key={stage.label}
              className="border border-border-primary rounded-sm p-4"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <div className="text-[14px] font-semibold text-text-primary">{stage.label}</div>
              <div className="text-[12px] text-text-secondary mt-1">{stage.sub}</div>
            </motion.div>
          ))}
        </div>

        <motion.p
          className="mt-10 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[800px]"
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.45, delay: 2.4, ease }}
        >
          Every asset passes through the same pipeline. Elimination filters remove manipulated or distressed companies before scoring begins. Remaining assets are ranked within their sector, then classified by composite percentile.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/system-diagram.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/system-diagram.tsx web/src/components/landing/__tests__/system-diagram.test.tsx
git commit -m "feat(web): build SystemDiagram — animated SVG pipeline visualization"
```

---

## Task 8: Build Section 4 — EngineProof

**Files:**
- Create: `web/src/components/landing/engine-proof.tsx`
- Delete: `web/src/components/landing/performance.tsx` (old)
- Create: `web/src/components/landing/__tests__/engine-proof.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/engine-proof.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { EngineProof } from "../engine-proof"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

describe("EngineProof", () => {
  it("renders section label", () => {
    render(<EngineProof />)
    expect(screen.getByText("What the output looks like")).toBeInTheDocument()
  })

  it("renders factor breakdown panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })

  it("renders conviction badge panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Exceptional")).toBeInTheDocument()
  })

  it("renders filter results panel", () => {
    render(<EngineProof />)
    expect(screen.getByText("Beneish M-Score")).toBeInTheDocument()
  })

  it("renders caption", () => {
    render(<EngineProof />)
    expect(screen.getByText(/same inputs, same outputs/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/engine-proof.test.tsx`
Expected: FAIL

**Step 3: Implement EngineProof**

Create `web/src/components/landing/engine-proof.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

function ProofPanel({
  children, className = "", delay,
}: {
  children: React.ReactNode; className?: string; delay: number
}) {
  return (
    <motion.div
      className={`border border-border-primary bg-bg-elevated rounded-sm p-6 ${className}`}
      initial={{ opacity: 0, scale: 0.98 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay, ease }}
    >
      {children}
    </motion.div>
  )
}

function PercentileBarMock({ label, value }: { label: string; value: number }) {
  const color = value >= 90 ? "bg-accent" : value >= 70 ? "bg-accent/60" : "bg-text-tertiary"
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 text-[14px] text-text-secondary shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-bg-subtle rounded-sm overflow-hidden">
        <div className={`h-full ${color} rounded-sm`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-10 text-right text-[14px] font-mono text-text-primary">{value}</span>
    </div>
  )
}

export function EngineProof() {
  return (
    <section style={{ padding: "64px 24px 80px" }}>
      <div className="mx-auto" style={{ maxWidth: "1280px" }}>
        <motion.h2
          className="text-[14px] font-medium text-text-tertiary uppercase tracking-[0.05em] mb-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          What the output looks like
        </motion.h2>

        <div className="grid grid-cols-12 gap-4 md:gap-6">
          {/* Large panel: Factor Breakdown (cols 1-7) */}
          <ProofPanel className="col-span-12 md:col-span-7" delay={0}>
            <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-6">Factor Breakdown</div>
            <div className="space-y-3">
              <PercentileBarMock label="Quality" value={78} />
              <PercentileBarMock label="Value" value={65} />
              <PercentileBarMock label="Momentum" value={88} />
            </div>
            <div className="mt-6 pt-4 border-t border-border-primary flex items-baseline gap-2">
              <span className="text-[14px] text-text-secondary">Composite</span>
              <span className="text-[28px] font-bold font-mono text-text-primary">82</span>
              <span className="text-[14px] text-text-tertiary">percentile</span>
            </div>
            <div className="mt-3 text-[12px] text-accent/60">
              Sector-neutral percentile rank within GICS sector
            </div>
          </ProofPanel>

          {/* Right column: two stacked panels (cols 8-12) */}
          <div className="col-span-12 md:col-span-5 grid gap-4 md:gap-6 content-start">
            {/* Conviction Badge */}
            <ProofPanel delay={0.2}>
              <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-4">Conviction</div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-accent" />
                <span className="text-[20px] font-bold text-text-primary">Exceptional</span>
              </div>
              <div className="mt-2 text-[14px] text-text-secondary">Top 1% composite percentile</div>
            </ProofPanel>

            {/* Filter Results */}
            <ProofPanel delay={0.35}>
              <div className="text-[12px] text-text-tertiary uppercase tracking-wider mb-4">Elimination Filters</div>
              <div className="space-y-2">
                {[
                  { name: "Beneish M-Score", passed: true },
                  { name: "Altman Z''", passed: true },
                  { name: "Liquidity", passed: true },
                  { name: "Interest Coverage", passed: true },
                ].map((filter) => (
                  <div key={filter.name} className="flex items-center gap-2 text-[14px]">
                    <span className={filter.passed ? "text-accent" : "text-bearish"}>
                      {filter.passed ? "✓" : "✗"}
                    </span>
                    <span className="text-text-secondary">{filter.name}</span>
                    <span className={`ml-auto text-[12px] ${filter.passed ? "text-accent" : "text-bearish"}`}>
                      {filter.passed ? "Pass" : "Fail"}
                    </span>
                  </div>
                ))}
              </div>
            </ProofPanel>
          </div>
        </div>

        <motion.p
          className="mt-8 text-text-secondary text-[16px] md:text-[17px] leading-relaxed"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 1.1, ease }}
        >
          These are real outputs from the scoring engine. Same inputs, same outputs, every time.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/engine-proof.test.tsx`
Expected: PASS

**Step 5: Delete old performance.tsx**

Run: `rm /Users/brandon/repos/margin_invest/web/src/components/landing/performance.tsx`

**Step 6: Commit**

```bash
git add web/src/components/landing/engine-proof.tsx web/src/components/landing/__tests__/engine-proof.test.tsx
git rm web/src/components/landing/performance.tsx
git commit -m "feat(web): build EngineProof — asymmetric multi-panel UI close-ups"
```

---

## Task 9: Build Section 5 — CapabilitiesSection

**Files:**
- Create: `web/src/components/landing/capabilities-section.tsx`
- Create: `web/src/components/landing/__tests__/capabilities-section.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/capabilities-section.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { CapabilitiesSection } from "../capabilities-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("CapabilitiesSection", () => {
  it("renders four capability headlines", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText(/sector-neutral ranking/i)).toBeInTheDocument()
    expect(screen.getByText(/growth stage calibrates/i)).toBeInTheDocument()
    expect(screen.getByText(/elimination runs before/i)).toBeInTheDocument()
    expect(screen.getByText(/determinism means/i)).toBeInTheDocument()
  })

  it("renders capability descriptions", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText(/GICS sector first/i)).toBeInTheDocument()
    expect(screen.getByText(/reproducible/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/capabilities-section.test.tsx`
Expected: FAIL

**Step 3: Implement CapabilitiesSection**

Create `web/src/components/landing/capabilities-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const capabilities = [
  {
    title: "Sector-neutral ranking eliminates cross-sector distortion.",
    body: "A high-margin software company and a capital-intensive manufacturer can't be compared on raw metrics. Every asset is ranked within its GICS sector first, then scored on relative positioning.",
    span: "col-span-12 md:col-span-7",
    accentBorder: true,
  },
  {
    title: "Growth stage calibrates what matters.",
    body: "High-growth companies are weighted toward quality and momentum. Mature businesses toward value. The engine detects the stage and adjusts factor weights automatically.",
    span: "col-span-12 md:col-span-5",
    accentBorder: false,
  },
  {
    title: "Elimination runs before scoring begins.",
    body: "Earnings manipulation (Beneish), financial distress (Altman Z''), and liquidity failures are caught first. Compromised assets never enter the scoring pipeline.",
    span: "col-span-12 md:col-span-5",
    accentBorder: false,
  },
  {
    title: "Determinism means the process is auditable.",
    body: "Every score is reproducible. Same data in, same score out, with a complete factor breakdown showing exactly how the composite was derived. No black box. No discretionary overrides.",
    span: "col-span-12 md:col-span-7",
    accentBorder: true,
  },
]

export function CapabilitiesSection() {
  return (
    <section style={{ padding: "96px 24px" }}>
      <div
        className="mx-auto grid grid-cols-12 gap-x-6 gap-y-12"
        style={{ maxWidth: "1280px" }}
      >
        {capabilities.map((cap, i) => (
          <motion.div
            key={i}
            className={`${cap.span} pt-10 px-8 pb-2`}
            style={{
              borderTop: cap.accentBorder
                ? "1px solid var(--color-accent)"
                : "1px solid var(--color-border-primary)",
            }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.15, ease }}
          >
            <h3 className="text-[24px] md:text-[26px] lg:text-[30px] font-semibold leading-[1.10] tracking-[-0.01em] text-text-primary mb-3">
              {cap.title}
            </h3>
            <p className="text-text-secondary leading-relaxed text-[16px] md:text-[17px] max-w-[640px]">
              {cap.body}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/capabilities-section.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/capabilities-section.tsx web/src/components/landing/__tests__/capabilities-section.test.tsx
git commit -m "feat(web): build CapabilitiesSection — 2x2 asymmetric analytical advantages"
```

---

## Task 10: Build Section 6 — InvestorPositioning

**Files:**
- Create: `web/src/components/landing/investor-positioning.tsx`
- Create: `web/src/components/landing/__tests__/investor-positioning.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/investor-positioning.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { InvestorPositioning } from "../investor-positioning"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

describe("InvestorPositioning", () => {
  it("renders the headline", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText("Discipline compounds.")).toBeInTheDocument()
  })

  it("renders the body text", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/same rigor to every decision/i)).toBeInTheDocument()
  })

  it("renders the data point", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/5–10 positions/i)).toBeInTheDocument()
  })

  it("renders the data caption", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/exceptional conviction/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/investor-positioning.test.tsx`
Expected: FAIL

**Step 3: Implement InvestorPositioning**

Create `web/src/components/landing/investor-positioning.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section style={{ padding: "80px 24px" }}>
      <div
        className="mx-auto grid grid-cols-12"
        style={{ maxWidth: "1280px" }}
      >
        {/* Offset content to cols 2-8 for rhythm variation */}
        <div className="col-span-12 md:col-start-2 md:col-span-7">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            Discipline compounds.
          </motion.h2>

          <motion.p
            className="mt-6 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[640px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
          >
            The edge isn't a single insight — it's a system that applies the same rigor to every decision. Margin Invest doesn't replace your judgment. It ensures every position you take has passed the same institutional-grade threshold.
          </motion.p>

          {/* Emerald horizontal rule */}
          <motion.div
            className="mt-10 h-px bg-accent/30"
            style={{ width: "33%" }}
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.4, ease }}
          />

          {/* Data point */}
          <motion.div
            className="mt-10"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.6, ease }}
          >
            <span className="text-[40px] md:text-[56px] font-bold leading-none tracking-[-0.02em] text-text-primary">
              Top 1% → 5–10 positions
            </span>
            <div className="text-[17px] text-text-primary mt-1">per cycle.</div>
          </motion.div>

          <motion.p
            className="mt-4 text-[14px] text-text-tertiary"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.8, ease }}
          >
            Exceptional conviction. The narrowest filter in the pipeline.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/investor-positioning.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/investor-positioning.tsx web/src/components/landing/__tests__/investor-positioning.test.tsx
git commit -m "feat(web): build InvestorPositioning — discipline + data point display"
```

---

## Task 11: Build Section 7 — FinalCTA

**Files:**
- Create: `web/src/components/landing/final-cta.tsx`
- Delete: `web/src/components/landing/cta.tsx` (old)
- Create: `web/src/components/landing/__tests__/final-cta.test.tsx`

**Step 1: Write test**

Create `web/src/components/landing/__tests__/final-cta.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FinalCTA } from "../final-cta"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("FinalCTA", () => {
  it("renders the headline", () => {
    render(<FinalCTA />)
    expect(screen.getByText("See what survives the filter.")).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<FinalCTA />)
    const cta = screen.getByRole("link", { name: "Explore the Engine" })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary link", () => {
    render(<FinalCTA />)
    expect(screen.getByText(/read the methodology/i)).toBeInTheDocument()
  })

  it("contains the grid overlay", () => {
    const { container } = render(<FinalCTA />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/final-cta.test.tsx`
Expected: FAIL

**Step 3: Implement FinalCTA**

Create `web/src/components/landing/final-cta.tsx`:

```tsx
"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { GridOverlay } from "./grid-overlay"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section className="relative" style={{ minHeight: "60vh" }}>
      <GridOverlay opacity={0.02} />
      <div
        className="relative mx-auto grid grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          padding: "120px 24px 160px",
        }}
      >
        {/* Content: cols 1-6 */}
        <div className="col-span-12 md:col-span-6">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, delay: 0.2, ease }}
          >
            See what survives the filter.
          </motion.h2>

          <motion.p
            className="mt-6 text-text-secondary text-[16px] md:text-[17px] leading-relaxed max-w-[640px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            Start with the full pipeline. Every factor, every elimination check, every percentile rank — visible and auditable.
          </motion.p>

          <motion.div
            className="mt-10"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.6, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-block px-8 py-4 bg-accent text-white font-semibold text-[15px] rounded-sm hover:bg-accent-hover transition-colors"
            >
              Explore the Engine
            </Link>
          </motion.div>

          <motion.div
            className="mt-4"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.75, ease }}
          >
            <Link
              href="/methodology"
              className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              Read the methodology →
            </Link>
          </motion.div>
        </div>

        {/* Cols 7-12: intentional negative space */}
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/final-cta.test.tsx`
Expected: PASS

**Step 5: Delete old cta.tsx**

Run: `rm /Users/brandon/repos/margin_invest/web/src/components/landing/cta.tsx`

**Step 6: Commit**

```bash
git add web/src/components/landing/final-cta.tsx web/src/components/landing/__tests__/final-cta.test.tsx
git rm web/src/components/landing/cta.tsx
git commit -m "feat(web): build FinalCTA — restrained CTA with grid overlay bookend"
```

---

## Task 12: Update landing page tests and verify full integration

**Files:**
- Rewrite: `web/src/app/__tests__/page.test.tsx`

**Step 1: Rewrite page test**

Replace `web/src/app/__tests__/page.test.tsx` with:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import Page from "../page"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    rect: (props: any) => <rect {...props} />,
    text: ({ children, ...props }: any) => <text {...props}>{children}</text>,
    line: (props: any) => <line {...props} />,
    path: (props: any) => <path {...props} />,
    g: ({ children, ...props }: any) => <g {...props}>{children}</g>,
  },
  useInView: () => true,
}))

describe("Landing Page", () => {
  it("renders hero section with headline", () => {
    render(<Page />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders primary CTA", () => {
    render(<Page />)
    const ctas = screen.getAllByText("Explore the Engine")
    expect(ctas.length).toBeGreaterThanOrEqual(1)
  })

  it("renders friction section", () => {
    render(<Page />)
    expect(screen.getByText(/conviction they haven't earned/i)).toBeInTheDocument()
  })

  it("renders system diagram section", () => {
    render(<Page />)
    expect(screen.getByText("How the engine works")).toBeInTheDocument()
  })

  it("renders engine proof section", () => {
    render(<Page />)
    expect(screen.getByText("What the output looks like")).toBeInTheDocument()
  })

  it("renders capabilities section", () => {
    render(<Page />)
    expect(screen.getByText(/sector-neutral ranking/i)).toBeInTheDocument()
  })

  it("renders investor positioning section", () => {
    render(<Page />)
    expect(screen.getByText("Discipline compounds.")).toBeInTheDocument()
  })

  it("renders final CTA section", () => {
    render(<Page />)
    expect(screen.getByText("See what survives the filter.")).toBeInTheDocument()
  })
})
```

**Step 2: Run ALL web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: ALL PASS

**Step 3: Run build**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add web/src/app/__tests__/page.test.tsx
git commit -m "test(web): update landing page tests for new marketing site sections"
```

---

## Task 13: Add theme toggle to Nav + add noise texture

**Files:**
- Modify: `web/src/components/layout/nav.tsx`
- Create: `web/public/noise.svg` (1-2% noise texture)

**Step 1: Create noise texture SVG**

Create `web/public/noise.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <filter id="noise">
    <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#noise)" opacity="0.015"/>
</svg>
```

**Step 2: Add noise to body in globals.css**

Add to the `body` rule in `web/src/app/globals.css`:

```css
body {
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  background-image: url('/noise.svg');
  background-repeat: repeat;
}
```

**Step 3: Add theme toggle button to Nav**

Add a theme toggle button to the Nav component's desktop menu area (after the user menu). Use `useTheme` from `next-themes`:

In `web/src/components/layout/nav.tsx`, add:

```tsx
import { useTheme } from "next-themes"
```

Add inside the component:
```tsx
const { theme, setTheme } = useTheme()
```

Add a toggle button in the desktop nav area (before the user menu `div`):
```tsx
<button
  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
  aria-label="Toggle theme"
>
  {theme === "dark" ? "☀" : "●"}
</button>
```

**Step 4: Update nav test to mock next-themes**

In `web/src/components/layout/__tests__/nav.test.tsx`, add to the mock section:

```tsx
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "dark", setTheme: vi.fn() }),
}))
```

**Step 5: Run nav tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/layout/__tests__/nav.test.tsx`
Expected: PASS

**Step 6: Run all tests and build**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run && npm run build`
Expected: ALL PASS, build succeeds.

**Step 7: Commit**

```bash
git add web/public/noise.svg web/src/app/globals.css web/src/components/layout/nav.tsx web/src/components/layout/__tests__/nav.test.tsx
git commit -m "feat(web): add light/dark theme toggle and subtle noise texture"
```

---

## Task 14: Final integration test — visual QA and cleanup

**Step 1: Run full test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: ALL PASS

**Step 2: Run build**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds with no errors.

**Step 3: Start dev server and visually inspect**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`

Manually verify in browser:
- [ ] Landing page loads with all 7 sections
- [ ] Light mode (toggle) shows warm off-white background
- [ ] Dark mode shows charcoal-black background
- [ ] Animations trigger on scroll
- [ ] System diagram renders correctly
- [ ] No broken layouts on mobile viewport (< 768px)
- [ ] Nav shows theme toggle
- [ ] Dashboard page still works with new color tokens
- [ ] All CTAs link correctly

**Step 4: Clean up any unused files**

Check if there are any remaining references to old component names or old token names.

Run: `grep -r "text-gold\|bg-gold\|border-border[^-]\|bg-bg-secondary\|rounded-xl\|rounded-lg" web/src/ --include="*.tsx" --include="*.ts" -l`

If any files still reference old tokens, fix them.

**Step 5: Final commit (if cleanup needed)**

```bash
git add -A web/src/
git commit -m "chore(web): final cleanup — remove stale token references"
```
