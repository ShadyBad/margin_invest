# Guides Feature Design

**Date**: 2026-02-19
**Status**: Approved

## Overview

Add a public-facing Guides section to Margin Invest that helps users understand the scoring engine, learn effective workflows, and troubleshoot data issues. Accessible via `/guides` in the top nav for both authenticated and unauthenticated users.

## Decisions

- **Content format**: MDX files in-repo (`web/src/content/guides/*.mdx`) loaded with `next-mdx-remote`
- **Index layout**: Card grid (responsive 1/2/3 columns)
- **Guide layout**: MDX content + sticky sidebar TOC with scroll-spy
- **Access**: Public (added to `PUBLIC_LINKS` in nav)
- **Content source of truth**: Real V3 dual-track engine logic — no invented formulas

## Architecture

### File Structure

```
web/src/
├── content/
│   └── guides/
│       ├── how-scoring-works.mdx
│       ├── elimination-filters.mdx
│       ├── using-margin-invest.mdx
│       ├── metrics-and-terminology.mdx
│       ├── position-sizing.mdx
│       └── data-freshness.mdx
├── app/
│   └── guides/
│       ├── page.tsx              # Index page (card grid)
│       └── [slug]/
│           └── page.tsx          # Individual guide (MDX render + TOC)
├── lib/
│   └── guides.ts                 # Frontmatter parser, guide loader, TOC extractor
└── components/
    └── guides/
        ├── guide-card.tsx        # Card for index grid
        ├── guide-layout.tsx      # Layout wrapper (content + sticky TOC)
        ├── table-of-contents.tsx # Sticky sidebar TOC with scroll-spy
        └── mdx-components.tsx    # Custom MDX renderers (Callout, Formula, Example)
```

### Routing

- `/guides` — public index, card grid of all guides
- `/guides/[slug]` — individual guide, dynamic route from MDX filename

### Data Flow

1. `guides.ts` reads `content/guides/*.mdx`, parses YAML frontmatter
2. Index page calls `getAllGuides()` → sorted metadata array → card grid
3. Detail page calls `getGuideBySlug(slug)` → frontmatter + raw MDX source
4. `next-mdx-remote` compiles MDX at render time with custom components
5. TOC extracted from H2/H3 headings via regex on raw MDX source

### Nav Change

Add `{ href: "/guides", label: "Guides" }` to `PUBLIC_LINKS` in `web/src/hooks/use-navigation.ts`. Already present in `APP_LINKS`.

## MDX Format

### Frontmatter Schema

```yaml
---
title: "How Scoring Works"
description: "Understand the dual-track scoring engine."
order: 1
updatedAt: "2026-02-19"
readingTime: 8
category: "Core Concepts"
---
```

### Custom Components

- **`<Callout type="info|warning|tip">`** — Highlighted box with left border accent. For important notes, pitfalls, tips.
- **`<Formula>`** — Monospace block for formulas. Light background, no syntax highlighting.
- **`<Example>`** — Walkthrough block with distinct background. For numerical examples.

Standard markdown handles everything else (headings, lists, tables, bold, code, links).

### Styling

MDX content renders in a prose container using Tailwind typography classes matched to existing color tokens. Dark mode automatic via theme system.

## Guide Content Plan

| # | Slug | Title | Key Sections |
|---|------|-------|-------------|
| 1 | `how-scoring-works` | How Scoring Works | 4-stage overview, Track A (Compounder) gates, Track B (Mispricing) gates, conviction determination, multiplicative scoring, worked example |
| 2 | `elimination-filters` | Elimination Filters Explained | All 6 filters with thresholds, sector adjustments, why filters exist, pitfall: "Why was my stock eliminated?" |
| 3 | `using-margin-invest` | Using Margin Invest Effectively | Daily/weekly workflow, reading the dashboard, interpreting conviction levels, decision checklist, pitfall: acting on WATCHLIST |
| 4 | `metrics-and-terminology` | Metrics & Terminology | ROIC, NOPAT, FCF Yield, Moat Durability, Compounding Power, Asymmetry Ratio, Catalyst Strength, Growth Stages, Conviction Levels |
| 5 | `position-sizing` | Position Sizing & Portfolio Construction | Max 10 positions, sizing by type + conviction, "both" at 20%, risk management, pitfall: over-concentrating |
| 6 | `data-freshness` | Data Sources & Freshness | Provider fallback chains, update cadences, quarterly lag, troubleshooting stale data, known limitations |

### Content Guardrails

- Educational and product-usage language only — no investment advice
- Every guide has a "Common Pitfalls" section
- Numerical examples use fictional but realistic values
- All thresholds and formulas match the real engine code

## UI Design

### Index Page

- Hero: `max-w-4xl` centered. Heading "Guides" + subtext.
- Grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`, `max-w-6xl`
- Cards: `bg-elevated`, `shadow-card` → `shadow-card-hover` on hover, rounded-lg, p-6. Title, description (2 lines), reading time + updated date footer. Entire card is a link. Subtle lift on hover.
- Animations: Viewport-triggered fade-in, staggered per card.

### Guide Page

- Two-column desktop (`max-w-6xl`): content (~70%) + sticky TOC (~25%, `sticky top-24`)
- Mobile: TOC hidden, full-width content
- Back link: "← All Guides" at top
- Title from frontmatter as heading-1, "Last updated" + reading time below in text-tertiary
- Content: Tailwind typography with existing text tokens

### Table of Contents

- Extracts H2 and H3 from MDX source
- H3s indented under parent H2
- Scroll-spy via `IntersectionObserver`, active item in `text-accent`, others `text-tertiary`
- CSS transitions on color, no Framer Motion

### Animations

Minimal. Cards fade-in on index page. Guide content page has no entry animations.

## Test Checklist

- [ ] Nav click routes to `/guides` for both authenticated and unauthenticated users
- [ ] Index page renders all 6 guide cards with correct metadata
- [ ] Clicking a card navigates to `/guides/[slug]`
- [ ] MDX content renders correctly (headings, lists, tables, custom components)
- [ ] TOC highlights correct section on scroll
- [ ] Deep links work (e.g., direct navigation to `/guides/how-scoring-works`)
- [ ] Mobile layout: TOC hidden, cards stack to single column
- [ ] Dark mode: all elements use correct theme tokens
- [ ] `next build` completes without errors
- [ ] Back link returns to `/guides`
