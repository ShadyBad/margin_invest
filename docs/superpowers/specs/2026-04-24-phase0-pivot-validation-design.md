# Phase 0 — Pivot Validation Strategy

**Date**: 2026-04-24
**Status**: Draft
**Goal**: Run 5 cheap, time-boxed experiments in parallel to kill or validate the retail thesis, surface B2B demand, and produce the legal/competitive research needed to make a pivot decision.

---

## 1. Strategic Context

### Pressure Test Outcome

WEAK / pivot required. The existing product (dashboard-first screener with three subscription tiers: Scout Free, Analyst $19/mo, Portfolio $49/mo) has not demonstrated product-market fit.

### Candidate Pivots

- **Pivot A — B2B API**: License the scoring engine to RIAs and fintech operators. Strongest technical fit — the engine is pure, deterministic, and already API-shaped. The governance pipeline (staged → approved → published) and reproducibility audits are differentiators a compliance-conscious buyer can't get from a Finviz scraper.
- **Pivot B — Consumer forensic scorecard**: Reframe the UI around single-ticker deep-dive scorecards instead of a 10-stock screener. Tests whether the value is in the depth, not the breadth.

### Phase 0 Purpose

Before choosing a pivot, run 5 parallel experiments to generate evidence for a decision gate. No new engine factors, no new Tier work, no new ML seeds until the gate clears. Each code workstream has a 5-day budget cap. Breach the cap → stop and brainstorm, don't extend.

### Guardrails

1. No new engine factors, no new Tier work, no new ML seeds until Phase 0 decision gate clears.
2. Every Phase 0 sub-task has a 5-day budget cap. Breach → stop and brainstorm.
3. Use `/flow:dev` for every code workstream. Acceptance criteria locked before implementation.
4. Use `superpowers:writing-plans` for anything estimated over 1 day.
5. Use `superpowers:test-driven-development` for engine-adjacent code.
6. Use `superpowers:verification-before-completion` before closing any workstream.
7. Archive current main to `archive/pre-pivot-2026-04-24` before any Phase 2 work starts.
8. No simultaneous Pivot A + Pivot B. One path, all-in.

---

## 2. Decision Gate

### Gate Inputs

All 5 workstreams must complete before evaluation.

| Workstream | Artifact | Quantitative Signal |
|---|---|---|
| 0.1 $10 list experiment | Live Stripe checkout, `experiment_signups` table, PostHog dashboard | Paid buyer count at day 30 |
| 0.2 Retention audit | `/tmp/retention-audit.csv` + stdout summary | WAU%, median sessions, 30-day churn |
| 0.3 B2B LOI pulse | 3 markdown files in `docs/b2b-pulse/` | LOI conversations from 100 cold emails |
| 0.4 Legal prep memo | `docs/legal/kelly-publishers-exclusion-memo.md` | Complete / not complete |
| 0.5 Competitor teardown | `docs/competitive/teardown.md` | Wedge identified / no wedge |

### Decision Rules

| Outcome | Condition | Next Step |
|---|---|---|
| **CONTINUE** | ≥100 buyers AND WAU >30% among paid users | Skip Phase 2. Go to Phase 3 (legal review). Scale existing product. |
| **PIVOT-A** | ≥3 LOI conversations from 100 cold emails | Archive main. Execute Phase 2A. |
| **PIVOT-B** | Retail pain is emotional, not workflow (qualitative judgment informed by 0.1 + 0.2 + 0.5) | Archive main. Execute Phase 2B. |
| **EXTEND** | 30–99 buyers OR 1–2 LOI conversations — signal is warm but inconclusive | Extend Phase 0 by 2 weeks max. Adjust distribution strategy or email targeting. One extension only — if the extended gate still misses, treat as STOP. |
| **STOP** | None of the above after extension | Re-brainstorm "what else could this engine become" or shut the project down. |

### Gate Rules

- CONTINUE requires both the buyer count AND the retention signal. Either alone is insufficient.
- PIVOT-B is the softest gate — it's a qualitative call, not a number. The teardown (0.5) and retention audit (0.2) inform it but don't mechanically trigger it.
- 0.4 (legal memo) and 0.5 (competitor teardown) are research-only — they inform the gate decision but don't independently trigger any outcome.
- No simultaneous Pivot A + Pivot B. Pick one, go all-in.

---

## 3. Workstream 0.1 — $10 List Experiment

**Goal**: Kill or validate the retail thesis with a one-shot $10 PDF purchase.

**Budget**: 5 days max. Ship or kill. No scope creep.

### Dependency: Daily Picks Archiver

The archiver (currently on `feature/daily-picks-archive`) must be merged to main and running in production before the experiment has real content. The archiver produces conviction-gated survivor lists daily from published V4 scores. The $10 PDF is a weekly digest packaging 5 trading days of archiver output with plain-English interpretation — narrative framing, factor context, "why these 10 survived and 4,900 didn't."

The archive is the provenance layer (structured JSON, hash chains, verifiability). The PDF is the product layer (human-readable narrative). Same data, different audiences.

**If the archiver isn't production-ready by experiment launch**: Ship the experiment page with a sample scorecard screenshot and static copy. First real PDF goes out after the archiver merges. This is acceptable — the experiment primarily tests willingness to pay, not PDF quality. The placeholder PDF is already in scope.

### Architecture

```
web/src/app/experiment/this-week/page.tsx  — server-rendered, no auth, no nav chrome
  ├── Headline + 3-bullet value prop + sample scorecard screenshot
  ├── Stripe Checkout button (one-shot $10, not subscription)
  └── PostHog events: page_view, checkout_click, purchase_complete

api/src/margin_api/routes/experiment.py  — new router
  ├── POST /api/v1/experiment/checkout  — creates Stripe Checkout session
  └── POST /api/v1/experiment/webhook   — handles checkout.session.completed
        ├── Insert into experiment_signups (email, paid_at, amount_cents, stripe_session_id)
        └── Trigger Resend email with placeholder PDF attachment

New table: experiment_signups
  - id (PK), email (text), paid_at (DateTime(timezone=True)), amount_cents (int),
    stripe_session_id (text, unique), created_at (DateTime(timezone=True))
  - Alembic migration with idempotent checks
```

### Reuse

- Existing `BillingService` (api/src/margin_api/services/billing.py, 134 lines) handles Stripe session creation. The experiment router wires it with a one-shot checkout mode instead of subscription.
- Existing `EmailService` (api/src/margin_api/services/email.py, 263 lines) handles Resend. Trigger with a placeholder PDF attachment.
- Existing PostHog integration on the frontend (layout.tsx, posthog/identify.tsx).

### UTM Variants

Two different UTM-tagged URLs pointing to the same page:
- `?utm_source=twitter&utm_campaign=list_v1`
- `?utm_source=reddit&utm_campaign=list_v1`

This is attribution tracking for distribution channels, not A/B copy testing on the page itself. One page, two distribution links.

### Landing Page Content

- Headline emphasizing the forensic/elimination framing
- Three bullet value prop: deterministic process, 4,900+ eliminated, tamper-evident track record
- One sample scorecard screenshot (static image)
- Stripe Checkout button
- No upsell, no navigation chrome, no signup required

### Tests

- One web test: page renders, `checkout_click` PostHog event fires on button click
- One API test: Stripe webhook handler inserts row into `experiment_signups` and triggers email

### Acceptance Criteria

1. URL is live on production Railway
2. Stripe Checkout works in both test and live mode
3. One end-to-end test purchase completes and lands in `experiment_signups`
4. PostHog dashboard shows all three events firing (page_view, checkout_click, purchase_complete)

### Success Metric (Human, Not Claude)

100 paid buyers in 30 days via organic FinTwit / r/SecurityAnalysis / r/ValueInvesting. Below 100 → retail thesis is dead. 30–99 → EXTEND gate (see Section 2).

---

## 4. Workstream 0.2 — Retention Audit

**Goal**: Measure real engagement of existing users. Answers: "Does anyone actually come back?"

**Budget**: 2 days max.

### Architecture

```
scripts/retention_audit.py  — standalone script, no UI, no migrations, no engine changes
  ├── Queries users table (registered before 2026-04-01)
  ├── For each user:
  │     - days_since_registration
  │     - distinct_active_days (count of unique days with a session)
  │     - weekly_active (boolean: any session in last 7 days)
  │     - score_requests (count of requests to /api/v1/scores/*)
  ├── Data source: PostHog events API (preferred — already integrated)
  │     - Filter by distinct_id and date range
  │     - Fallback: count score API requests from DB if PostHog data is insufficient
  └── Output:
        - /tmp/retention-audit.csv (one row per user)
        - stdout summary line: WAU_pct, median_sessions, 30day_churn_pct
```

### Data Source Decision

PostHog is already capturing frontend events. The script queries PostHog's export API for per-user session counts, filtering by `distinct_id` (user ID) and date range. If PostHog data doesn't cover the full user base (e.g., integration was added after some users registered), fall back to counting requests against `/api/v1/scores/*` from available server-side data.

### Tests

One unit test covering the aggregation logic with a fake dataset (in-memory list of user records, no DB required).

### Acceptance Criteria

1. CSV produced at `/tmp/retention-audit.csv`
2. Stdout summary line prints WAU_pct, median_sessions, 30day_churn_pct
3. Test passes

### Success Metric (Human)

WAU >30% among paid users. Below → product does not retain regardless of price.

### Caveat

This measures the current dashboard product, not the pivot candidates. Low WAU kills the CONTINUE path but does not directly inform PIVOT-A or PIVOT-B.

---

## 5. Workstream 0.3 — B2B LOI Pulse

**Goal**: Surface B2B demand signal before building anything. Research and drafting only — zero code changes.

**Budget**: 2 days for the documents.

### Deliverables

| File | Contents |
|---|---|
| `docs/b2b-pulse/cold-email-v1.md` | 120-word cold email pitching the engine as a licensable API. Free 30-day pilot for a signed LOI at $500/mo. Three subject-line variants. |
| `docs/b2b-pulse/landing-copy.md` | One-page spec for a `/b2b` landing page (copy only, not implementation). Sections: problem, engine, data sources, governance pipeline, API surface, pricing placeholder, CTA. |
| `docs/b2b-pulse/target-list.md` | Criteria and sources for first 50 RIAs (<$1B AUM) and first 50 fintech/newsletter operators. Cites Form ADV, SEC RIA database, LinkedIn searches. Describes search queries to run — does not invent firm names. |

### Pitch Framing

Lead with the governance pipeline (staged → approved → published) and the deterministic scoring guarantee as differentiators. Secondary: 34 registered worker functions, 15 cron jobs, EDGAR integration, 13F pipeline, risk factor diffing — the infrastructure depth that's hard to replicate.

### Process

Brainstorm the pitch angle before drafting. Stress-test whether RIAs care about determinism (they do — compliance) vs. fintech operators (they care about data freshness and API simplicity).

### Acceptance Criteria

1. All three markdown files exist and contain substantive content
2. Cold email is ≤120 words
3. Target list describes real search methodologies, not invented firms

### Success Metric (Human)

3 signed LOIs at $500/mo+ from 100 cold emails in 14 days. The human sends the emails, not Claude.

---

## 6. Workstream 0.4 — Regulatory Attorney Prep Memo

**Goal**: Produce a research memo to bring to a securities attorney, focusing on whether Margin Invest's features qualify for the SEC publisher's exclusion under the Investment Advisers Act of 1940.

**Budget**: 1–2 days.

### Deliverable

`docs/legal/kelly-publishers-exclusion-memo.md`

### Contents

1. **Publisher's exclusion summary**: Plain-English explanation anchored in *Lowe v. SEC* (472 U.S. 181, 1985) and relevant SEC no-action letters.
2. **Disqualifying factors**: Case law and enforcement history on what crosses the line — personalization, tailored advice, targeted subscription offerings.
3. **Feature risk assessment**: Rate each Margin Invest feature red / yellow / green:
   - Kelly-sized per-user position recommendations → **RED**
   - Saved portfolios → **YELLOW**
   - Personalized score alerts → **YELLOW**
   - Public scored list (no personalization) → **GREEN**
   - Single-ticker forensic scorecard (no sizing) → **GREEN**
4. **Attorney questions**: Three prioritized questions for a one-hour consultation.
5. **Estimated consultation cost**: Typical hourly rate for a securities specialist.

### Constraints

- Cite real sources. Flag uncertainty explicitly in writing.
- Do not fabricate case numbers or no-action letter references.
- This is research support, not legal advice.

### Acceptance Criteria

1. Memo file exists with all 5 sections populated
2. All case citations are real and verifiable
3. Feature risk ratings are present with reasoning

### Relationship to Phase 3

This memo is the input packet for the attorney consultation in Phase 3. Phase 3 cannot start without it.

---

## 7. Workstream 0.5 — Competitor Teardown

**Goal**: Honest competitive positioning. Identify a real wedge or accept the moat diagnosis.

**Budget**: 2 days.

### Deliverable

`docs/competitive/teardown.md`

### Competitors

Stockopedia, Finviz Elite, GuruFocus, Koyfin, Simply Wall St, TIKR.

### Contents

- **Feature matrix**: Rows are features (scoring, screening, 13F tracking, risk factor analysis, backtesting, API access, alerts, portfolio tools). Columns are competitors. Cells note presence / depth.
- **Pricing**: Current pricing for each competitor with URLs.
- **Hardest-to-replicate feature**: Per-competitor, the single feature Margin Invest lacks that would be hardest to build.
- **Honest wedge assessment**: One paragraph answering "What do we do that none of them do?" No marketing voice, no adjectives. If the honest answer is "nothing differentiated," write that.

### Limitations

Several competitors gate features behind login/paywall (Stockopedia, Finviz Elite). The teardown is based on public pricing pages, free-tier features, and published documentation. This is noted explicitly — partial coverage but still useful for positioning.

### Acceptance Criteria

1. Teardown file exists with all four sections
2. Feature matrix covers all 6 competitors
3. Wedge assessment is honest (no marketing language)

### Success Metric (Human)

You read the file and either identify a real wedge or accept the moat diagnosis.

---

## 8. Phase 2A — B2B API Pivot (Directional)

**Executes only if PIVOT-A clears the gate.** Each task below gets its own brainstorming → spec → plan cycle after the decision gate. These descriptions are directional, not implementation-ready.

**Pre-Phase-2 action**: `git branch archive/pre-pivot-2026-04-24 main && git push -u origin archive/pre-pivot-2026-04-24`

### 2A.1 Public API Surface

New FastAPI router at `/api/public/v1/` exposing: `GET /scores/{ticker}`, `GET /filters/{ticker}`, `GET /factors/{ticker}`, `GET /13f/{ticker}`, `GET /risk_delta/{ticker}`. Bearer-token auth via `customer_api_keys` table (hashed key, customer ID, tier, timestamps, revocation). Redis-backed per-caller rate limiting. Per-request telemetry to `api_usage_events`. Auto-generated OpenAPI spec. No changes to internal `/api/v1/` routes. TDD. Coverage ≥90% on new router. One Alembic migration with idempotent checks.

### 2A.2 Developer Docs + Sample Client

Routes under `web/src/app/developers/`: getting-started, reference (consuming OpenAPI spec), pricing, changelog. Python sample client at `clients/python/margin_client/` with minimal surface: `MarginClient(credential)`, `get_score(ticker)`, `get_filters(ticker)`. Publish-ready pyproject.toml. Pricing page: Starter $500/mo (10K calls), Growth $2,000/mo (100K), Scale (custom). Coverage ≥90% for client.

### 2A.3 Self-Serve Onboarding + Billing

Signup form at `/developers/signup` with captcha and rate limiting. Stripe subscription checkout for the three B2B tiers. Webhook-driven credential provisioning (on `checkout.session.completed`, create API key, send welcome email via Resend). Admin view at `/admin/api-customers` with usage stats and credential management (rotate, revoke). Cancellation webhook revokes credentials and notifies customer. TDD webhook handler with Stripe event fixtures. Coverage ≥90%.

---

## 9. Phase 2B — Consumer Forensic Scorecard Pivot (Directional)

**Executes only if PIVOT-B clears the gate.** Each task below gets its own brainstorming → spec → plan cycle after the decision gate.

**Pre-Phase-2 action**: Same archive branch as 2A.

### 2B.1 Reframe UI Around Single-Ticker Scorecards

New landing page at `/` with single ticker input → `/scorecard/{TICKER}` rendering: M-Score, Z-Score, factor decomposition, 13F presence, moat classification, risk factor delta — each with plain-English interpretation. Move 10-survivors screener behind `/advanced/*`. Remove "10 survivors" framing from all marketing copy. Free tier: 3 scorecards per IP per day (no signup). Paid tier: unlimited + history + alerts at $9/mo. Engine untouched. TDD on all new components. Coverage ≥80%.

### 2B.2 Shareability + Viral Loops

Copy-link button with PostHog `scorecard_share` event. Tweet button with prefill: "Forensic scorecard for $TICKER: [composite tier] — M:[score] Z:[score] — {url}". New endpoint `/scorecard/{TICKER}/og.png` returning branded 1200×630 Open Graph image. Admin dashboard `/admin/viral` with shares/day, clicks/share, share-to-signup conversion. No engine changes.

### 2B.3 Remove Kelly Sizer from Public Product

Remove Kelly sizing section from Portfolio tier UI and public API responses. Keep all `engine/` Kelly code and tests intact — no deletion. Gate Kelly behind `/admin/kelly-preview` (admin session auth already exists). Update pricing page to drop "position sizing" from Portfolio feature list. Regenerate `AnalysisDisclaimerModal` copy. No engine deletion, no DB migration. Coverage ≥80% on changed web files.

---

## 10. Phase 3 — Legal Sign-Off

**Not a Claude Code task.** Human actions only.

1. Book a one-hour consultation with a securities attorney using `docs/legal/kelly-publishers-exclusion-memo.md` (from workstream 0.4) as the input packet.
2. Do not launch any personalized-sizing tier publicly until written sign-off arrives.
3. Budget: $500. Timeline: within 2 weeks of Phase 0 decision gate.
4. Store attorney letter at `docs/legal/attorney-signoff-YYYY-MM-DD.pdf`.

---

## How to Know This Plan Worked

| Phase | Success Condition |
|---|---|
| Phase 0 | Five deliverables on disk and a written decision outcome (CONTINUE / PIVOT-A / PIVOT-B / EXTEND / STOP) |
| Phase 2A | 3+ paying B2B customers on the new API with 99%+ uptime over a rolling 14 days |
| Phase 2B | `/scorecard/{TICKER}` shipped, ≥1,000 unique scorecards rendered in 30 days, ≥50 paid subscribers |
| Phase 3 | Attorney letter filed at `docs/legal/attorney-signoff-YYYY-MM-DD.pdf` |
