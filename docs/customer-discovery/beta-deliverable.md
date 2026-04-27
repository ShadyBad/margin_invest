# Margin Invest Founder Beta — Day-35 Deliverable

**Drafted**: 2026-04-27 (during Pre-flight)
**Status**: Pre-Phase 3 reference. Linked from the Stripe Checkout description so customers consent to specific scope, not a vibe.

**Customer charge date**: Day of Stripe Checkout completion (target: sprint Day 21).
**Beta access date**: 14 calendar days after charge (target: sprint Day 35).
**Subscription**: $49/month recurring. Cancel anytime via self-serve Stripe customer portal.

---

## Included on Day 35

The Founder Beta is access to the running Margin Invest application. The build state at Day 35 reflects the platform as it exists today (2026-04-27) plus any exploratory Phase 5 work (Days 21-28) committed before launch.

### Authentication and account
- Email + password sign-up, sign-in, password reset
- Two-factor authentication (TOTP) — optional, recommended
- Self-serve account settings (email, password, MFA, billing portal link)
- Stripe customer portal for subscription management (update card, cancel, view invoices)

### Asset coverage
- ~5,300 US-listed equities indexed (NYSE + NASDAQ, market cap > $50M)
- Daily price refresh
- Quarterly fundamentals from EDGAR (XBRL parser covers 26 financial fields)
- Point-in-time historical data: 217K snapshots, 12.8M prices, 224K universe memberships back to 2009

### Scoring and signals
- Composite score per ticker (0-100 percentile, sector-neutral)
- Five-factor breakdown: quality, value, momentum, sentiment, growth (each as percentile)
- Composite tier classification (strong / stable / emerging / weak / failed)
- Six elimination filters with pass/fail breakdown per ticker
- Sector champion identification
- Filter failure diagnostics on the asset detail page

### Pages and tools
- **Landing / dashboard** (`/`, `/dashboard`): daily picks, top 5 candidates, factor radar overview
- **Explore** (`/explore`): full universe browse with sector and tier filters
- **Asset detail** (`/asset/[ticker]`): per-ticker score, factor radar, filter pass/fail, sector micro-bar, valuation audit, formula tooltips, deterministic-output badge, sector-neutral banner, historical score chart, risk-factor delta card (where 10-K diff data is available)
- **Smart Money** (`/smart-money`): 13F fund tracker, market signals, clone lab, market pulse — quarterly accumulation signals from 300+ tracked managers
- **Backtesting** (`/backtesting`): historical strategy tester with rebalance audits, filter failure breakdowns, Kelly position sizing
- **Track record** (`/track-record`): historical pick performance
- **Methodology** (`/methodology`): scoring formulas explained, with auditable derivations
- **Guides** (`/guides`): explainer content
- **Onboarding** (`/onboarding`): walkthrough for new users
- **Status** (`/status`): system status indicators

### Forensic and trust features
- Deterministic-output badge on every score (same inputs = same outputs)
- Sector-neutral banner explaining ranking methodology
- Formula tooltips on every percentile
- Filter failure diagnostics (why a ticker was eliminated)
- Failed-comparison view (this ticker vs sector champion)
- Selectivity funnel (5,300 → final picks visualization)
- Correlation heatmap (cross-ticker)
- Sector breakdown
- Historical score evolution

### API access (read-only)
- Authenticated read endpoints: scores, dashboard, sectors, asset detail, backtest, smart-money analytics, risk diffing
- API documentation at `/api-docs`
- Rate-limited; suitable for personal-use scripts and watchlists

---

## Not included on Day 35 (roadmap, NOT promised)

These features may exist in code but are NOT part of the Founder Beta scope. Mentioning here so customers don't expect them.

- **Mobile app**: web-only on Day 35.
- **Real-time intraday quotes**: end-of-day prices only.
- **Options data, futures, crypto, FX**: US equities only.
- **International equities**: domestic only.
- **Custom portfolio tracking with cost basis**: read-only watchlist supported; full portfolio P&L is not.
- **Tax-loss harvesting suggestions**: not in scope.
- **Direct broker integration / order routing**: research and analysis only; no execution.
- **Email or push alerts**: not on Day 35.
- **Custom scoring formulas / user-tuneable weights**: scoring is deterministic and standardized; no user-tunable parameters.
- **Multi-user / team accounts**: single-user accounts only.
- **White-label / API resale rights**: API access is for personal use only.
- **Earnings call transcript analysis**: not in scope.
- **Insider transaction alerts**: not in scope.
- **Sector rotation models**: not in scope.

---

## Known limitations on Day 35

Customers should know what they're getting. Honest disclosure prevents churn surprise.

### Data and coverage
- US equities only; market-cap floor ~$50M
- Quarterly fundamentals refresh on a delay (filings ingested as EDGAR publishes; lag of 1-90 days from fiscal quarter close)
- Some international ADRs may have incomplete fundamentals
- Companies with non-standard fiscal years may show partial data on quarterly views

### Scoring caveats
- Scoring is deterministic, sector-neutral, percentile-based — does NOT predict short-term price movements
- Composite tier ("strong", "stable", "emerging", "weak", "failed") is a forensic classification, NOT a buy/sell recommendation
- Backtesting uses point-in-time data with corporate-action adjustments; results do not guarantee future performance
- Risk factor diffing is a standalone signal, NOT integrated into the composite score (separate overlay on asset detail page)

### Operational limitations
- ML model promotion requires manual human approval (governance gate); model updates may lag market events
- Score drift circuit breaker pauses publication if changes exceed threshold (rare but possible)
- Some experimental features may appear in the UI behind disabled toggles; they are not part of the Founder Beta scope

### Performance
- Asset detail pages load in ~1-2s typical
- Backtesting runs synchronously; complex multi-year backtests may take 30-60s
- Daily picks refresh once per day (overnight)

### Support
- Founder Beta tier: email support with 48-business-hour SLA
- No live chat, no phone support
- Known-issue tracker available via `/status` page

---

## Cancellation policy

- Cancel anytime via the Stripe customer portal (linked from `/settings`)
- No questions asked; no clawback
- Pro-rated refunds: NO. The current billing cycle is not refunded; cancellation takes effect at the next renewal
- Exception: refund-on-NO-GO (sprint-internal). If the customer-discovery sprint reaches a Day-21 NO-GO verdict, all charged subscriptions are refunded in full within 48 hours of decision and access is revoked. This is a one-time sprint-period guarantee, not an ongoing policy.

---

## Data and privacy

- Customer email and Stripe customer ID stored for billing; no payment-card data stored on Margin Invest infrastructure (Stripe-managed)
- No tracking pixels, no analytics SDKs that share PII to third parties
- Account deletion: email support; data purged within 30 days

---

## Day 35 launch checklist (for the founder)

Before sending beta-access emails on Day 35, verify:

- [ ] Auth flow works end-to-end (sign-up → login → MFA → settings)
- [ ] Stripe portal link in `/settings` resolves correctly
- [ ] Each beta customer's email is whitelisted (if access-gated) or has a working account
- [ ] Daily picks have refreshed in the last 24h
- [ ] No critical errors in the last 24h of logs
- [ ] `/status` page reflects current state honestly
- [ ] Beta-access email template ready (see `docs/customer-discovery/beta-access-email-template.md` — to be drafted in exploratory Phase 5 if not already)
