# Methodology & Guides Content Rework — Design Document

**Date**: 2026-02-26
**Status**: Approved
**Approach**: Narrative Spine with Reference Wings (progressive disclosure)

## Context

The public Methodology page and 6 educational Guides need a full-scope rework addressing:
- **Organization**: Content is accurate but poorly structured for discovery
- **Accessibility**: Reads too academic for retail investors; impenetrable for beginners
- **Trust gaps**: Formulas and citations exist but don't build sufficient confidence
- **Staleness**: Guides describe V3 pipeline; V4 scoring, ML pipeline, and 13F institutional data are undocumented

### Audience

Three personas served simultaneously via progressive disclosure:
1. **Complete beginners** — "What should I buy?" Want dead-simple summaries.
2. **Self-directed retail investors** — Comfortable with financial basics, want to understand the system.
3. **Quant-aware sophisticates** — Want formulas, thresholds, and academic citations to verify rigor.

### Success Criteria

- Reduce support questions about "how does this work?" and "can I trust this?"
- Build trust that converts skeptical visitors into users
- Match or exceed documentation quality of Portfolio123, Validea, and Composer

---

## 1. Diagnostic Framework

### Evaluation Dimensions

Score each existing content section 1-5 across:

| Dimension | Assessment criteria |
|-----------|-------------------|
| **Clarity** | Can a retail investor understand the core point in one reading? Average sentence length < 25 words? |
| **Accuracy** | Does content match the actual V4 scoring pipeline, ML adjustments, and 13F signals? |
| **Structure** | Logical flow? Can readers skip to what they need? |
| **Trust signals** | Formulas shown? Sources cited? Limitations acknowledged? |
| **Cognitive load** | How many new concepts per section? Terms defined before use? |
| **Completeness** | Any gaps where a reader would need to ask support? |
| **Competitive parity** | How does this section compare to equivalent content from Portfolio123/Validea/Composer? |

### Reviewer Questions

1. Does this section describe what the system *actually* does today, or what it did in V3?
2. Could a beginner extract a useful mental model from just the non-expanded content?
3. Could a quant investor verify the math from the expanded content?
4. Where would a skeptic say "prove it" — and is the proof provided?
5. Are there jargon terms used before being defined?
6. Does every formula have a plain-English sentence explaining what it measures and why it matters?

### User Analytics to Collect

Before rewriting, pull from analytics:
- Bounce rates on `/methodology` and each `/guides/[slug]` page
- Time-on-page for each guide
- Scroll depth on methodology page
- Support ticket topics related to "how does scoring work" or methodology questions

### Known Staleness Issues

- Guides describe V3 dual-track scoring; V4 pipeline with ML adjustments is undocumented
- No mention of 13F institutional accumulation signals (implemented 2026-02-25)
- ML pipeline (cluster models, VAE, rank IC thresholds) not referenced anywhere
- `insider_percentile` and `institutional_percentile` may reference old hardcoded values
- Batched ingest pipeline replaces old `full_ingest` — data freshness guide is outdated
- Position sizing guide doesn't reflect current allocation matrix

---

## 2. Content Restructure — Information Architecture

### Approach: Narrative Spine with Reference Wings

- **Methodology** = narrative journey of a stock through the full pipeline (progressive disclosure)
- **Concept Guides** = deep-dive specifications for individual topics
- **Workflow Guides** = task-oriented how-to content
- **Reference** = linkable glossary of all terms

### New Site Map

```
/methodology                     ← Narrative Spine (progressive disclosure)
│
├── The Pipeline Story            "Follow AAPL through every stage"
│   ├── Universe & Screening      7,000+ stocks → eligible universe
│   ├── Elimination Gauntlet      6 binary filters, fail-fast
│   ├── Factor Scoring            Quality · Value · Momentum (20 factors)
│   ├── Dual-Track Conviction     Compounder vs. Mispricing gates
│   ├── ML Refinement             Cluster models, VAE, rank IC  [NEW]
│   ├── 13F Smart Money Overlay   Institutional accumulation    [NEW]
│   └── Position Sizing           Conviction × opportunity type matrix
│
├── Transparency Commitment       "Same inputs = same outputs"
└── CTA                           "Explore the dashboard"

/guides                          ← Categorized into three types
│
├── Concepts (deep dives)
│   ├── Elimination Filters       Thresholds, sector adjustments, citations
│   ├── Scoring Factors           All 20 factors with formulas  [replaces Metrics & Terminology]
│   ├── Conviction & Tracks       Gate logic, multiplicative scoring
│   ├── ML Pipeline               How models train, what they adjust  [NEW]
│   ├── Institutional Signals     13F data, accumulation scoring  [NEW]
│   └── Data Sources & Freshness  Providers, lag times, limitations
│
├── Workflows (task-oriented)
│   ├── Getting Started           First-time user quickstart  [NEW]
│   ├── Reading the Dashboard     Cards, badges, colors, ordering
│   ├── Analyzing a Stock         Asset detail page walkthrough  [NEW]
│   ├── Building a Portfolio      Position sizing, diversification
│   └── Weekly Review Process     What to check and when
│
└── Reference
    └── Glossary                  All terms, alphabetical, linkable anchors  [NEW]
```

### Content Placement Rules

| Content type | Methodology | Concept Guide | Workflow Guide |
|-------------|-------------|---------------|----------------|
| What the system does | Summary + expandable detail | Full specification | — |
| Why it works that way | One sentence per stage | Academic citations, research context | — |
| Formulas & thresholds | In expandable panels | Primary home (canonical source) | Link to concept guide |
| Worked examples | One running example (e.g., AAPL) | Factor-specific examples | — |
| How to use the platform | — | — | Step-by-step instructions |
| Visuals & diagrams | Pipeline flow, funnel | Factor breakdowns, formulas | UI screenshots, annotated |

### Key Structural Changes

1. "How Scoring Works" guide content moves *into* methodology page as the narrative spine
2. "Metrics & Terminology" splits: terms → Glossary, factor details → "Scoring Factors" guide
3. "Using Margin Invest" splits into three workflow guides (Getting Started, Analyzing a Stock, Weekly Review)
4. Two entirely new concept guides: ML Pipeline and Institutional Signals
5. New Glossary as a linkable reference (every term links here on first use)
6. "Position Sizing" guide moves to Workflows as "Building a Portfolio"

---

## 3. Trust & Authority Improvements

### Transparency Integration

1. **Every formula gets a "Why This Matters" sentence.** Plain-English explanation directly above each formula explaining what it measures and why investors care. Currently, formulas like `Asymmetry Ratio = Upside / Downside` are shown without context.

2. **Expandable "Technical Detail" panels.** Default view shows the narrative. Expand to see: exact formula, threshold values, sector adjustments, academic citation, worked numerical example. Serves beginners (collapsed) and quants (expanded).

3. **"Verify It Yourself" blocks.** For key claims, include a concrete way the user can verify: "Enter the same ticker on two different days with the same data. The scores will be identical." Converts claims into testable promises.

4. **"Known Limitations" sections.** Each concept guide ends with honest limitations. Examples:
   - "ML models require 90+ days of scoring history before they activate"
   - "13F filings have a 45-day reporting lag"
   - "Newly IPO'd companies lack sufficient history for reliable scoring"

### Visual Assets

| Visual | Location | Purpose |
|--------|----------|---------|
| Pipeline flow diagram | Methodology hero | Full journey at a glance |
| Filter funnel | Methodology → Elimination stage | Visualize narrowing |
| Factor radar/breakdown | Scoring Factors guide | Factor contributions |
| Conviction gate flowchart | Conviction guide | Trace path through gates |
| Data freshness timeline | Data Sources guide | Update cadences visually |
| Annotated dashboard screenshot | Getting Started workflow | Orient new users |
| Annotated asset detail screenshot | Analyzing a Stock workflow | What each section means |
| Position sizing matrix | Building a Portfolio | Allocation table |

### Credibility Signals

- **Academic citations**: Surface prominently in guides (currently in code metadata but not always shown in MDX)
- **Data provenance**: Name providers explicitly (FMP, Polygon, SEC EDGAR) with update frequencies
- **Version transparency**: Show "Pipeline Version: V4" and last-updated dates prominently
- **Backtest results**: Link to backtesting page as empirical evidence
- **Open methodology framing**: "We show our work because we trust our work"

### Competitive Benchmarking Targets

- **Portfolio123**: Publishes factor definitions with formulas but not ML pipeline — we exceed this with full transparency
- **Validea**: Names academic models (Greenblatt, Piotroski) — we match this with citations
- **Composer**: Publishes strategy logic as code — our transparency commitment parallels this
- **Our edge**: Full ML + 13F pipeline disclosure is rare; most platforms hide their model internals

---

## 4. Content Review Process

### Internal Review (You)

- Verify all formulas match actual codebase implementation
- Test workflow guides by following the steps end-to-end
- Spot-check 3-5 factor calculations against engine code
- Confirm V4 pipeline description matches `v4_scoring.py` and related services

### Professional Content Editor

**Role**: Quality gate for clarity, tone, and audience-appropriateness. Not a ghostwriter — we produce the content, they review it.

**Qualifications**:
- Fintech or financial services writing experience
- Technical writing background (can evaluate formula clarity for non-experts)
- Familiarity with progressive disclosure UX patterns
- Portfolio of published methodology/whitepaper content
- Basic understanding of quant finance concepts

**Where to find**: Upwork (filter "fintech writer"), Contently, LinkedIn ("content strategist" + "fintech/wealthtech"). Budget: $75-150/hr or $2,000-4,000 fixed scope.

### Legal/Compliance Review

**Scope**:
- Verify all disclaimers are present and adequate
- Ensure no content constitutes investment advice
- Check that claims are defensible (e.g., "deterministic" is verifiable; "best" would not be)
- Review "Not built for" section for regulatory sufficiency
- Confirm risk disclosure language meets fintech standards
- Flag any performance claims that need qualification

**Who**: Your legal counsel, a fintech compliance consultant, or a securities attorney familiar with investment tool disclaimers.

### Final Approval Checklist

- [ ] Every formula has a plain-English explanation
- [ ] Every technical term is defined in Glossary and linked on first use
- [ ] No jargon used before definition
- [ ] Methodology narrative reads coherently with all expandables collapsed
- [ ] Expandables contain accurate V4 pipeline details
- [ ] All academic citations correctly attributed
- [ ] Known Limitations sections are honest and specific
- [ ] Tone: authoritative but not arrogant, transparent but not apologetic
- [ ] Content matches actual system behavior (spot-check formulas vs. codebase)
- [ ] "Verify It Yourself" blocks contain actionable, testable claims
- [ ] Workflow guides testable: follow steps → reach described outcome
- [ ] Mobile: expandable panels work on small screens
- [ ] Legal: no content constitutes investment advice; disclaimers present
- [ ] Data freshness claims match current pipeline cadences
- [ ] Competitive parity with Portfolio123/Validea/Composer docs
- [ ] SEO: meta descriptions, structured data for educational content

---

## 5. Deliverables & Timeline

### Phases

| Phase | What | Who | Output |
|-------|------|-----|--------|
| **1. Audit** | Score every existing section against diagnostic framework. Competitive benchmark. Pull user analytics. | Claude + you | Audit report with gap analysis |
| **2. Architecture** | Implement new IA: restructure routes, create MDX scaffolding, build new components, add Glossary infrastructure. | Claude | New page structure, components, empty MDX files |
| **3. Methodology Rewrite** | Write narrative spine — one stock through V4 pipeline. All 7 stages including ML and 13F. Expandable technical panels. | Claude + you (review) | Complete `/methodology` page |
| **4. Guide Rewrites** | Write all 11 guides + glossary. Update concept guides to V4. Create 5 new guides. Restructure existing content. | Claude + you (review) | Complete `/guides` content |
| **5. Visual Assets** | Create/update diagrams, annotated screenshots, data tables. Update existing visuals for V4. | Claude | Updated visual components |
| **6. Internal Review** | Review all content for accuracy. Spot-check formulas vs. codebase. Test workflow guides. | You | Revision notes |
| **7. Professional Edit** | External fintech editor reviews for clarity, tone, audience-appropriateness per checklist. | External editor | Edited content |
| **8. Legal/Compliance** | Review regulatory language, disclaimers, investment advice boundaries, defensibility of claims. | Legal counsel | Compliance sign-off |
| **9. Publish** | Deploy updated content. Redirect changed URLs. Update in-app metadata to match new guide structure. | Claude | Live content |

### Phase Dependencies

```
Phase 1 (Audit) → Phase 2 (Architecture) → ┬─ Phase 3 (Methodology)  ─┐
                                             ├─ Phase 4 (Guides)       ├→ Phase 6 (Internal) → ┬─ Phase 7 (Editor)  ─┐
                                             └─ Phase 5 (Visuals)     ─┘                       └─ Phase 8 (Legal)   ─┘→ Phase 9 (Publish)
```

Phases 3-5 run in parallel. Phases 7-8 run in parallel.

### New Components to Build

| Component | Type | Purpose |
|-----------|------|---------|
| `<TechnicalDetail>` | MDX component | Expandable panel for formulas, thresholds, citations |
| `<VerifyItYourself>` | MDX component | Testable claim blocks with user instructions |
| `<KnownLimitations>` | MDX component | Honest limitation disclosures |
| Glossary page | Route + component | `/guides/glossary` with linkable term anchors |
| Guide category tabs | Component | Concepts / Workflows / Reference sections on `/guides` index |

### Content Inventory (Final)

| Item | Status | Lines (est.) |
|------|--------|-------------|
| Methodology narrative (7 sections + expandables) | Rewrite | ~500 |
| Elimination Filters (concept) | Update | ~150 |
| Scoring Factors (concept) | New (from Metrics split) | ~300 |
| Conviction & Tracks (concept) | New (from How Scoring split) | ~200 |
| ML Pipeline (concept) | New | ~150 |
| Institutional Signals (concept) | New | ~150 |
| Data Sources & Freshness (concept) | Update | ~120 |
| Getting Started (workflow) | New | ~100 |
| Reading the Dashboard (workflow) | Update (from Using MI) | ~120 |
| Analyzing a Stock (workflow) | New | ~150 |
| Building a Portfolio (workflow) | Update (from Position Sizing) | ~120 |
| Weekly Review Process (workflow) | New (from Using MI) | ~100 |
| Glossary (reference) | New | ~200 |
| **Total** | | **~2,360** |

### Transparency Level

Full transparency: V4 scoring pipeline, ML refinement layer (cluster models, VAE, rank IC thresholds), 13F institutional accumulation signals, and all factor formulas are disclosed publicly. Competitive moat comes from execution speed and data quality, not secrecy.
