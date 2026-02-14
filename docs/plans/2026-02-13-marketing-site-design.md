# Marketing Site Design

**Date:** 2026-02-13
**Scope:** Replace existing landing page with bespoke adaptive (light/dark) marketing site
**Stack:** Next.js 15 (existing web/ package), Inter Tight font, Tailwind v4, Framer Motion
**Approach:** Editorial Scroll — single continuous scroll with varied compositional rhythm per section

---

## Decisions

- **Deployment:** Replaces existing `web/src/app/page.tsx` and `web/src/components/landing/`
- **Typography:** Inter Tight (free, Google Fonts, self-hosted via `next/font`)
- **Color scope:** Full app rebrand — new warm off-white / charcoal-black + emerald palette applies to all pages including dashboard

---

## 1. Narrative Architecture

| # | Section | Intent | Density |
|---|---------|--------|---------|
| 1 | Declarative Philosophy (Hero) | Establish authority immediately. One bold thesis, no explanation. The visitor decides in 3 seconds if this is for them. | Sparse — 80% whitespace |
| 2 | Retail Friction Recognition | Name the pain precisely: emotion, noise, inconsistency. Create recognition without condescension. | Medium — text-dominant, tight vertical rhythm |
| 3 | Analytical System Diagram | Reveal the engine's architecture as a conceptual flow: Filters -> Quantitative Scoring -> Composite -> Classification. A system blueprint, not a feature list. | Dense — diagram occupies ~70% of viewport |
| 4 | Engine UI Proof | Show, don't tell. Tight crops of actual dashboard: factor breakdown, conviction badge, percentile bar. Prove the system produces real output. | Dense — multiple image panels, minimal copy |
| 5 | Strategic Capabilities | Reframe features as analytical advantages: sector-neutral ranking, growth-stage calibration, elimination filters, deterministic scoring. | Medium-high — 4 capabilities in asymmetric layout |
| 6 | Empowered Investor Positioning | Shift from product to identity. You're not buying a tool; you're adopting a discipline. | Medium — balanced text + subtle visual |
| 7 | Confident Restrained CTA | One clear action. No urgency tricks. Confidence is the conversion mechanism. | Sparse — generous whitespace, single CTA |

**Vertical rhythm map:**

```
[1] Hero           ~90vh  Expansive
[2] Friction       ~50vh  Tighter
[3] Diagram        ~85vh  Dominant
[4] UI Proof       ~75vh  Dense, multi-panel
[5] Capabilities   ~65vh  Medium
[6] Positioning    ~55vh  Breathing
[7] CTA            ~60vh  Generous
```

---

## 2. Layout Blueprint

### Section 1: Declarative Philosophy (Hero)

- **Grid:** Content cols 1-8, cols 9-12 intentional negative space
- **Composition:** H1 at ~35% from top (not centered). Subhead 24px below. Two CTAs inline 40px below subhead. Faint 3% opacity geometric grid overlay spans full viewport width.
- **Light/Dark:** Light: H1 `#121212`, bg `#F4F3EF`. Dark: H1 `#E8E8E6`, bg `#0D0F12`. CTA emerald fill in both.
- **Component:** `<HeroSection />`

### Section 2: Retail Friction Recognition

- **Grid:** Asymmetric two-column. Left cols 1-5 (bold friction statement). Right cols 7-12 (three friction points with 2px emerald left-border accents).
- **Composition:** Left has single H2. Right has three H3+body stacked 48px apart. No icons. Text density carries weight. Tighter padding than hero (80px vs 160px).
- **Light/Dark:** Left-border accent `#0E4F3A` at 40% (light) / lifted emerald at 50% (dark). Right-column body in secondary text color.
- **Component:** `<FrictionSection />`

### Section 3: Analytical System Diagram

- **Grid:** Full 12-column span
- **Composition:** Small H2 label top-left (cols 1-4). Diagram occupies cols 1-12. Horizontal flow: Filters (left) -> Quantitative Scoring (center, expanded into Quality/Value/Momentum) -> Composite (right) -> Classification (far right). Nodes are rectangular 1px border. Connectors 1px with directional indicators. Caption below.
- **Light/Dark:** Light: `#121212` 1px borders, connectors at 20%. Dark: `#E8E8E6` 1px borders on `#151820`, connectors at 20%. Active node: emerald border pulse on scroll trigger.
- **Component:** `<SystemDiagram />` — SVG-based with Framer Motion path animations

### Section 4: Engine UI Proof

- **Grid:** Asymmetric multi-panel. Large panel cols 1-7 (~400px). Two stacked panels cols 8-12 (~195px each).
- **Composition:** Large: factor breakdown with percentile bars. Top-right: conviction badge close-up. Bottom-right: filter results pass/fail. Thin annotation lines connect elements to labels. 1px borders, subtle elevation.
- **Light/Dark:** Light: panels `#FFFFFF` with `#E0DED8` border, shadow `0 2px 8px rgba(0,0,0,0.04)`. Dark: panels `#151820` with `#252830` border, no shadow. Annotation lines: emerald at 60%.
- **Component:** `<EngineProof />` with `<ProofPanel />`

### Section 5: Strategic Capabilities

- **Grid:** 2x2 asymmetric. Row 1: cols 1-7 (A, wide) + cols 8-12 (B, narrow). Row 2: cols 1-5 (C, narrow) + cols 6-12 (D, wide).
- **Composition:** Each capability: H3 headline + 2-sentence body + thin top border (1px). No icons. 40px top padding, 32px side padding. 24px column gap, 48px row gap. One emerald top-border per row.
- **Light/Dark:** Top borders charcoal 15% (light) / off-white 10% (dark). Emerald accent borders on one per row.
- **Component:** `<CapabilitiesSection />` with `<CapabilityBlock />`

### Section 6: Empowered Investor Positioning

- **Grid:** Single-column, cols 2-8 (offset from left edge)
- **Composition:** H2 headline. 2-3 sentence body. Thin emerald horizontal rule (cols 2-5). Large data point display ("Top 1% -> 5-10 positions per cycle"). Small caption below.
- **Light/Dark:** Minimal differences. Horizontal rule emerald at 30%.
- **Component:** `<InvestorPositioning />`

### Section 7: Confident Restrained CTA

- **Grid:** Content cols 1-6. Right half empty.
- **Composition:** H2 headline. One body sentence. Single primary CTA 40px below. Small secondary text link. Generous padding (120px top, 160px bottom). Geometric grid overlay returns at 2% (bookend with hero).
- **Light/Dark:** Same as hero delta.
- **Component:** `<FinalCTA />`

---

## 3. Copy Deck

### Tone Rules

- Headlines are conclusions, not invitations
- No exclamation marks
- No superlatives or startup buzzwords
- CTAs are calm imperatives

### Section 1: Hero

- **H1:** Structure outperforms emotion.
- **Subhead:** A deterministic scoring engine that evaluates every US equity through the same institutional-grade framework — no discretion, no narrative bias, no exceptions.
- **Primary CTA:** Explore the Engine
- **Secondary CTA:** View methodology

### Section 2: Friction Recognition

- **H2:** Most investment decisions are made with conviction they haven't earned.
- **Friction 1 H3:** Emotion enters before analysis finishes.
- **Friction 1 Body:** Sentiment shifts between checking a position and deciding what to do about it. The process isn't flawed — it's absent.
- **Friction 2 H3:** Inconsistent frameworks produce inconsistent results.
- **Friction 2 Body:** Switching between screeners, newsletters, and intuition means every decision uses different criteria. There's no baseline to evaluate against.
- **Friction 3 H3:** Retail tools measure activity, not quality.
- **Friction 3 Body:** Volume, price movement, trending tickers — these describe what happened. They don't tell you whether the underlying business justifies a position.

### Section 3: System Diagram

- **Label:** How the engine works
- **Diagram nodes:** Elimination Filters (Beneish M-Score, Altman Z'', Liquidity, Coverage) -> Quality 35% (Gross Profitability, ROIC-WACC, Accrual Ratio, F-Score) / Value 30% (EV/FCF, Shareholder Yield, DCF Margin, Acquirer's Multiple) / Momentum 35% (Price 12-1mo, Earnings SUE, Insider Clusters, Institutional Flow) -> Composite Score (Sector-neutral percentile) -> Classification (Exceptional, High Conviction, Watchlist)
- **Caption:** Every asset passes through the same pipeline. Elimination filters remove manipulated or distressed companies before scoring begins. Remaining assets are ranked within their sector, then classified by composite percentile.

### Section 4: Engine UI Proof

- **Label:** What the output looks like
- **Large panel annotation:** Factor breakdown — percentile ranks across quality, value, and momentum within the asset's GICS sector.
- **Top-right annotation:** Conviction classification derived from composite percentile position.
- **Bottom-right annotation:** Binary elimination filters. A single failure excludes the asset from scoring entirely.
- **Caption:** These are real outputs from the scoring engine. Same inputs, same outputs, every time.

### Section 5: Strategic Capabilities

- **A H3:** Sector-neutral ranking eliminates cross-sector distortion.
- **A Body:** A high-margin software company and a capital-intensive manufacturer can't be compared on raw metrics. Every asset is ranked within its GICS sector first, then scored on relative positioning.
- **B H3:** Growth stage calibrates what matters.
- **B Body:** High-growth companies are weighted toward quality and momentum. Mature businesses toward value. The engine detects the stage and adjusts factor weights automatically.
- **C H3:** Elimination runs before scoring begins.
- **C Body:** Earnings manipulation (Beneish), financial distress (Altman Z''), and liquidity failures are caught first. Compromised assets never enter the scoring pipeline.
- **D H3:** Determinism means the process is auditable.
- **D Body:** Every score is reproducible. Same data in, same score out, with a complete factor breakdown showing exactly how the composite was derived. No black box. No discretionary overrides.

### Section 6: Empowered Investor Positioning

- **H2:** Discipline compounds.
- **Body:** The edge isn't a single insight — it's a system that applies the same rigor to every decision. Margin Invest doesn't replace your judgment. It ensures every position you take has passed the same institutional-grade threshold.
- **Data point:** Top 1% -> 5-10 positions per cycle.
- **Caption:** Exceptional conviction. The narrowest filter in the pipeline.

### Section 7: Final CTA

- **H2:** See what survives the filter.
- **Body:** Start with the full pipeline. Every factor, every elimination check, every percentile rank — visible and auditable.
- **Primary CTA:** Explore the Engine
- **Secondary:** Read the methodology

---

## 4. Design System Spec

### Typography

**Families:**
- Primary: Inter Tight (loaded via `next/font/google`, weights 400, 500, 600, 700)
- Mono: Geist Mono (data values, scores)

**Scale (modular ratio ~1.2):**

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `--text-h1` | 68px | 700 | 0.98 | -0.03em | Hero headline |
| `--text-h2` | 44px | 700 | 1.02 | -0.02em | Section headlines |
| `--text-h3` | 30px | 600 | 1.10 | -0.01em | Capability headlines |
| `--text-body` | 17px | 400 | 1.55 | 0 | Paragraph text |
| `--text-body-lg` | 20px | 400 | 1.50 | 0 | Subhead / lead-in |
| `--text-caption` | 14px | 500 | 1.40 | 0.01em | Annotations, labels |
| `--text-data` | 14px mono | 500 | 1.30 | 0.02em | Scores, numbers |
| `--text-display` | 56px | 700 | 1.00 | -0.02em | Large data points |

**Rules:**
- All headlines left-aligned, no centered text on landing page
- H1 used once (hero). H2 for section heads. H3 for sub-items.
- Body max-width: 640px
- Mono exclusively for numerical data

**Responsive:**

| Breakpoint | H1 | H2 | H3 | Body |
|------------|----|----|-----|------|
| >=1280px | 68px | 44px | 30px | 17px |
| 768-1279px | 52px | 36px | 26px | 16px |
| <768px | 40px | 30px | 24px | 16px |

### Color Tokens

```css
/* Light Mode */
--bg-primary:       #F4F3EF;
--bg-elevated:      #FFFFFF;
--bg-subtle:        #ECEAE4;
--text-primary:     #121212;
--text-secondary:   #5C5C5C;
--text-tertiary:    #8A8A86;
--accent:           #0E4F3A;
--accent-hover:     #0B3E2E;
--accent-subtle:    rgba(14, 79, 58, 0.08);
--border-primary:   #D8D6D0;
--border-subtle:    rgba(18, 18, 18, 0.08);
--surface-overlay:  rgba(18, 18, 18, 0.03);

/* Dark Mode */
--bg-primary:       #0D0F12;
--bg-elevated:      #151820;
--bg-subtle:        #1A1D24;
--text-primary:     #E8E8E6;
--text-secondary:   #9B9B98;
--text-tertiary:    #6B6B68;
--accent:           #1A7A5A;
--accent-hover:     #1F8F6A;
--accent-subtle:    rgba(26, 122, 90, 0.10);
--border-primary:   #252830;
--border-subtle:    rgba(232, 232, 230, 0.06);
--surface-overlay:  rgba(232, 232, 230, 0.03);
```

**Semantic tokens:**
```css
--color-success:    var(--accent);
--color-danger:     #C74B50 / #D45A5F;
--color-warning:    #B8860B / #D4A843;
--color-neutral:    var(--text-tertiary);
```

**Accent rule:** Emerald at <=10% visual weight. Only on: CTA fills, active/hover states, left-border accents (S2), diagram node highlights (S3), capability top-borders (S5, 2 of 4), horizontal rule (S6).

### Grid + Spacing

- 12 columns, max 1280px, 24px column gap
- Outer margin: `max(24px, calc((100vw - 1280px) / 2))`

**Spacing scale (8px base):**

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 8px | Minimum gap |
| `--space-2` | 16px | Inline spacing |
| `--space-3` | 24px | Column gap, component padding |
| `--space-4` | 32px | Inter-element spacing |
| `--space-5` | 40px | CTA spacing, block padding |
| `--space-6` | 48px | Between capability items |
| `--space-8` | 64px | Tight section padding |
| `--space-10` | 80px | Medium section padding |
| `--space-12` | 96px | Default section padding |
| `--space-16` | 128px | Generous section padding |
| `--space-20` | 160px | Hero/CTA padding |

**Section vertical rhythm:**

| Section | Top | Bottom |
|---------|-----|--------|
| 1 Hero | 160px | 160px |
| 2 Friction | 80px | 96px |
| 3 Diagram | 96px | 96px |
| 4 UI Proof | 64px | 80px |
| 5 Capabilities | 96px | 96px |
| 6 Positioning | 80px | 80px |
| 7 CTA | 120px | 160px |

### Component Styling

**Buttons:**
- Primary: emerald fill, white text, 2px border-radius max, padding 16px 32px, weight 600, 15px
- Ghost: transparent, 1px `--border-primary`, `--text-primary`, same padding
- Hover: primary darkens; ghost gets `--accent-subtle` bg
- No pills. No large rounded corners.

**Panels/Cards:**
- 1px `--border-primary`, bg `--bg-elevated`, 0-2px radius
- Light: `box-shadow: 0 1px 4px rgba(0,0,0,0.03)`
- Dark: no shadow, border + brightness

**Diagram nodes:**
- Rectangular, 1px border, `--text-caption` label, weight 500
- Connectors: 1px `--border-subtle`, small arrow terminators
- Active: border + label transition to `--accent`

**Annotation lines:**
- 1px `--accent` at 50%, 4px circular terminal, `--text-caption` label

**Geometric grid overlay:**
- SVG thin-line grid pattern
- 3% opacity (hero), 2% (final CTA)
- `--text-primary` at specified opacity, full viewport width

---

## 5. Motion Choreography

**Global:** Easing `cubic-bezier(0.22, 1, 0.36, 1)`, duration 450-700ms, scroll trigger at 15% from bottom, play once.

### Section 1: Hero (page load, no scroll trigger)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| Grid overlay | Fade 0->3% | 700ms | 0ms |
| H1 | Y+20px fade | 600ms | 200ms |
| Subhead | Y+16px fade | 500ms | 400ms |
| Primary CTA | Y+12px fade | 450ms | 550ms |
| Secondary CTA | Y+12px fade | 450ms | 650ms |

### Section 2: Friction (scroll-triggered)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| H2 | Y+24px fade | 550ms | 0ms |
| Friction 1 | Y+20px fade | 500ms | 150ms |
| Border 1 | ScaleY 0->1 (top origin) | 450ms | 200ms |
| Friction 2 | Y+20px fade | 500ms | 300ms |
| Border 2 | ScaleY 0->1 | 450ms | 350ms |
| Friction 3 | Y+20px fade | 500ms | 450ms |
| Border 3 | ScaleY 0->1 | 450ms | 500ms |

### Section 3: System Diagram (scroll-triggered, ~2.8s total)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| Label | Fade | 400ms | 0ms |
| Filter nodes | Fade + scale 0.96->1.0 | 500ms | 200ms |
| Connector Filters->Scoring | SVG stroke draw | 600ms | 500ms |
| Quality node | Fade + scale | 500ms | 700ms |
| Value node | Fade + scale | 500ms | 850ms |
| Momentum node | Fade + scale | 500ms | 1000ms |
| Connectors->Composite | SVG stroke draw | 500ms | 1200ms |
| Composite node | Fade + scale + emerald flash | 600ms | 1500ms |
| Connector->Classification | SVG stroke draw | 500ms | 1800ms |
| Classification | Fade + scale | 500ms | 2100ms |
| Caption | Fade | 450ms | 2400ms |

### Section 4: Engine UI Proof (scroll-triggered)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| Large panel | Scale 0.98->1.0 fade | 600ms | 0ms |
| Top-right panel | Scale 0.98->1.0 fade | 500ms | 200ms |
| Bottom-right panel | Scale 0.98->1.0 fade | 500ms | 350ms |
| Annotation 1 | SVG draw + label fade | 450ms | 600ms |
| Annotation 2 | SVG draw + label fade | 450ms | 750ms |
| Annotation 3 | SVG draw + label fade | 450ms | 900ms |
| Caption | Fade | 400ms | 1100ms |

### Section 5: Capabilities (scroll-triggered)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| Cap A | Y+20px fade | 500ms | 0ms |
| Border A | ScaleX 0->1 (left origin) | 500ms | 100ms |
| Cap B | Y+20px fade | 500ms | 200ms |
| Border B | ScaleX 0->1 | 500ms | 300ms |
| Cap C | Y+20px fade | 500ms | 400ms |
| Cap D | Y+20px fade | 500ms | 550ms |

### Section 6: Positioning (scroll-triggered)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| H2 | Y+20px fade | 550ms | 0ms |
| Body | Y+16px fade | 500ms | 200ms |
| Rule | ScaleX 0->1 (left) | 600ms | 400ms |
| Data point | Y+12px fade | 600ms | 600ms |
| Caption | Fade | 400ms | 800ms |

### Section 7: Final CTA (scroll-triggered)

| Element | Animation | Duration | Delay |
|---------|-----------|----------|-------|
| Grid overlay | Fade 0->2% | 700ms | 0ms |
| H2 | Y+20px fade | 550ms | 200ms |
| Body | Y+16px fade | 500ms | 400ms |
| CTA | Y+12px fade | 500ms | 600ms |
| Secondary link | Fade | 400ms | 750ms |

---

## 6. Anti-Template Compliance Checklist

| Anti-Pattern | How Avoided | Section |
|---|---|---|
| 3-feature card rows | 2x2 asymmetric (7+5 / 5+7 cols), no uniform grid | S5 |
| Testimonial carousels | Zero testimonials. Product proves itself via diagram + UI panels. | N/A |
| Centered giant gradient hero | Left-aligned cols 1-8, no gradient, no centering | S1 |
| Evenly spaced modular stacking | Padding varies 64-160px, no two sections match | All |
| Evenly repeated section patterns | Six different grid configs across seven sections | All |
| Rounded pill UI | Max 2px border-radius on all elements | All |
| Startup-bro fintech aesthetic | Declarative copy, no hype, muted emerald <=10% | All |
| Crypto visual language | No gradients, blobs, neon, glass morphism | S3, S4 |
| 100vh section stacking | No section exactly 100vh, heights vary 50-90vh | All |
| Icon-driven feature lists | Zero icons in capabilities, text + border accents only | S5 |
| Generic stock photography | Zero photos. SVG diagrams, UI crops, geometric overlays. | S3, S4 |
| Centered everything | All left-aligned, asymmetric grids, offset cols | All |

---

## 7. ASCII Wireframes

### Section 1: Hero (~90vh)

```
+----------------------------------------------------------------------+
| ..............................  grid overlay 3%  .................... |
|                                                                      |
|  _________________________ (thin rule, col 1-6)                      |
|                                                                      |
|  Structure outperforms                                               |
|  emotion.                          [NEGATIVE SPACE]                  |
|                                    [  cols 9-12   ]                  |
|  A deterministic scoring engine                                      |
|  that evaluates every US equity                                      |
|  through the same institutional-                                     |
|  grade framework.                                                    |
|                                                                      |
|  [Explore the Engine]  View methodology                              |
|                                                                      |
+----------------------------------------------------------------------+
```

### Section 2: Friction (~50vh)

```
+----------------------------------------------------------------------+
|                                                                      |
|  Most investment           |# Emotion enters before                  |
|  decisions are made        |  analysis finishes.                     |
|  with conviction           |  Sentiment shifts between...            |
|  they haven't earned.      |                                         |
|                            |# Inconsistent frameworks                |
|  (cols 1-5, H2)           |  produce inconsistent results.          |
|                            |  Switching between screeners...         |
|                            |                                         |
|                            |# Retail tools measure                   |
|                            |  activity, not quality.                 |
|                            |  Volume, price movement...              |
|                                                                      |
|  # = 2px emerald left-border accent                                  |
+----------------------------------------------------------------------+
```

### Section 3: System Diagram (~85vh)

```
+----------------------------------------------------------------------+
|  How the engine works                                                |
|                                                                      |
|  +-----------+      +------------------------------+                 |
|  | ELIMINATION|      |    QUANTITATIVE SCORING      |   +--------+   |
|  |  FILTERS  |----->|                              |-->|COMPSITE|   |
|  |           |      | +-------+ +-----+ +-------+ |   | SCORE  |   |
|  | Beneish   |      | |Quality| |Value| |Moment.| |   +---+----+   |
|  | Altman    |      | | 35%   | | 30% | | 35%   | |       |        |
|  | Liquidity |      | +-------+ +-----+ +-------+ |       v        |
|  | Coverage  |      +------------------------------+   +--------+   |
|  +-----------+                                         |CLASSIF.|   |
|                                                        |Except. |   |
|                                                        |High    |   |
|                                                        |Watch   |   |
|                                                        +--------+   |
|                                                                      |
|  Every asset passes through the same pipeline...                     |
+----------------------------------------------------------------------+
```

### Section 4: Engine UI Proof (~75vh)

```
+----------------------------------------------------------------------+
|  What the output looks like                                          |
|                                                                      |
|  +-------------------------------------+  +------------------------+ |
|  |                                     |  |  CONVICTION BADGE      | |
|  |  FACTOR BREAKDOWN                   |  |  * Exceptional         | |
|  |                                     |  |    Top 1%              | |
|  |  Quality   ########----  78th       |  +------------------------+ |
|  |  Value     ######------  65th       |                             |
|  |  Momentum  ##########--  88th       |  +------------------------+ |
|  |              . annotation --------- |  |  FILTER RESULTS        | |
|  |  Composite: 82nd percentile         |  |  + Beneish     Pass    | |
|  |                                     |  |  + Altman      Pass    | |
|  +-------------------------------------+  |  + Liquidity   Pass    | |
|                                            |  x Coverage    Fail   | |
|                                            +------------------------+ |
|  Real outputs. Same inputs, same outputs.                            |
+----------------------------------------------------------------------+
```

### Section 5: Capabilities (~65vh)

```
+----------------------------------------------------------------------+
|                                                                      |
|  #_________________________________  ________________________        |
|  Sector-neutral ranking              Growth stage calibrates         |
|  eliminates cross-sector             what matters.                   |
|  distortion.                                                         |
|  A high-margin software company      High-growth weighted toward     |
|  and a capital-intensive...          quality and momentum...         |
|  (cols 1-7, WIDE)                   (cols 8-12, NARROW)             |
|                                                                      |
|  ________________________  #_________________________________        |
|  Elimination runs before   Determinism means the process             |
|  scoring begins.           is auditable.                             |
|  Earnings manipulation,    Every score is reproducible...            |
|  financial distress...                                               |
|  (cols 1-5, NARROW)       (cols 6-12, WIDE)                         |
|                                                                      |
|  # = emerald top-border accent (1 per row)                           |
+----------------------------------------------------------------------+
```

### Section 6: Positioning (~55vh)

```
+----------------------------------------------------------------------+
|                                                                      |
|     Discipline compounds.                                            |
|                                                                      |
|     The edge isn't a single insight -- it's a                        |
|     system that applies the same rigor to every                      |
|     decision.                                                        |
|                                                                      |
|     #________________________ (emerald rule, cols 2-5)               |
|                                                                      |
|     Top 1% -> 5-10 positions                                        |
|     per cycle.                                                       |
|                                                                      |
|     Exceptional conviction.                                          |
|                                                                      |
|     (all content offset to cols 2-8)                                 |
+----------------------------------------------------------------------+
```

### Section 7: Final CTA (~60vh)

```
+----------------------------------------------------------------------+
| ..............................  grid overlay 2%  .................... |
|                                                                      |
|                                                                      |
|  See what survives                 [NEGATIVE SPACE]                  |
|  the filter.                       [  cols 7-12   ]                  |
|                                                                      |
|  Start with the full pipeline.                                       |
|  Every factor, every elimination                                     |
|  check, every percentile rank.                                       |
|                                                                      |
|  [Explore the Engine]                                                |
|  Read the methodology ->                                             |
|                                                                      |
|                                                                      |
+----------------------------------------------------------------------+
```
