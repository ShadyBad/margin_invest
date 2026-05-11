# Margin Invest

> **Status: decommissioned.** This was a production deterministic equity-scoring platform. Live service shut down May 2026. Repo is kept public as a portfolio piece. No further development.

A deterministic, evidence-first equity research platform. Ingest financial data, run elimination filters, score the survivors with a five-factor percentile model, overlay 13F smart-money signals, and size positions with the Kelly criterion. Same inputs, same outputs, every time.

The product was killed because the market for it wasn't there. The engineering is left here intact.

## What's interesting about this repo

If you're hiring for an AI/ML or backend role and you opened this looking for signal, here's what to look at:

- **`engine/`** — pure Python scoring library, zero web deps, ~3,345 tests, golden-value regression suite. Same `(asset, market_state)` → same `CompositeScore` every time. Temperature=0 for any LLM call.
- **`engine/margin_engine/ml/`** — multi-seed validation. 20 seeds per training cycle, distributional gate (median IC > 0.15, CV < 0.50, worst seed > 0.05), only the best-qualified model gets staged. Plus full reproducibility audits — environment snapshot persisted for every training run.
- **`api/margin_api/services/risk_diffing/`** — proprietary signal pipeline. Semantic diffing of consecutive 10-K Item 1A Risk Factors using Voyage `voyage-finance-2` embeddings + Claude Haiku 4.5 with prompt caching. ~$0.019 / filing, ~$57 to process the full universe. Eval harness gates promotion: ≥70% precision, ≥60% recall, 5% regression budget.
- **`api/margin_api/workers/`** — 34 ARQ workers, 15 cron jobs. Daily ingest → score → stage → human approval → publish. Circuit breakers on score drift, ingestion failure rate, ML regression.
- **`api/margin_api/governance/`** — staged → approved → published pipeline for every scoring run and ML model promotion. Audit trail to `governance_events`. Webhook delivery with HMAC-SHA256 signing and 5-attempt retry.
- **`web/`** — Next.js 16, React 19, Tailwind v4. Custom design tokens, no shadcn. `~1,576` Vitest tests.
- **`evals/risk_factor_diffing/`** — manual eval harness with 5 seeded golden cases (SVB, Enron, WorldCom, Wirecard, Luckin). This is the pattern I'd reach for on any LLM feature: prompt change → measure → ship or revert.

## Architecture

Monorepo, three packages:

| Package | Purpose | Stack |
| --- | --- | --- |
| `engine/` | Scoring library, zero web deps | Python 3.13, `uv` workspace |
| `api/` | FastAPI service + ARQ workers | FastAPI, SQLAlchemy 2.0, asyncpg, Alembic, Redis, ARQ |
| `web/` | Marketing site + dashboard | Next.js 16, React 19, Tailwind v4, Vitest |

Supporting:

- **DB:** PostgreSQL 16
- **Cache / queue:** Redis + ARQ
- **Auth:** `next-auth` v5 + WebAuthn + TOTP
- **Payments (was):** Stripe
- **Email (was):** Resend
- **Telemetry (was):** Sentry + PostHog
- **LLM:** Anthropic SDK direct (Haiku 4.5 + Sonnet 4.6 with prompt caching), Voyage AI embeddings (`voyage-finance-2`)
- **ML:** scikit-learn, LightGBM, PyTorch
- **Deploy (was):** Railway — `margin_invest` API service + `margin-worker` ARQ service

## The scoring pipeline (short version)

```
~3,056 tickers
     │
     ▼
Elimination filters (fail-fast)
  ├─ liquidity, market cap, history
  ├─ moat classification
  ├─ ROIC-conditional conviction gates
  └─ mediocrity gate w/ trajectory override
     │
     ▼  (~250 survivors)
Five-factor percentile scoring (sector-neutral)
  ├─ quality, growth, value, profitability, momentum
  └─ weighted geometric mean composite w/ floor
     │
     ▼  (~50 survivors)
13F smart-money overlay
  └─ new positions + crowded trades signal
     │
     ▼  (~10–25 survivors)
Risk Factor diffing (proprietary)
  └─ semantic diff of consecutive 10-K Item 1A
     │
     ▼
Kelly criterion position sizing
     │
     ▼
Stage → human approve → publish
```

## What this repo is **not**

- Not investment advice. SEC publisher's exclusion alignment was a design constraint, not the goal.
- Not running. The Railway services are dead, Stripe is closed, DNS is parked or lapsed.
- Not actively maintained. Don't open PRs. Fork if you want.

## Running it locally (if you really want to)

```bash
# prereqs: uv, Node 22+, Docker, Postgres 16, Redis
brew install postgresql@16 redis
createuser -s margin
psql -c "ALTER USER margin WITH PASSWORD 'margin_dev';"
createdb -O margin margin_invest

cp .env.example .env  # fill in keys for FMP, Polygon, Anthropic, Voyage, etc.

uv sync
docker compose up -d  # Redis
uv run alembic upgrade head
uv run uvicorn margin_api.app:create_app --factory --reload

cd web
pnpm install
pnpm dev
```

Tests:

```bash
uv run pytest engine/tests/ -v
uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py
cd web && npx vitest run
```

## Why it was killed

Three reasons in priority order:

1. **No user pull.** Deterministic equity scoring is a thing retail traders *say* they want and don't pay for. The Stripe data was clear.
2. **Compliance gravity.** Every shipped feature dragged in fresh legal review. The product-market fit needed to be much stronger to justify it.
3. **My time was better spent.** Higher-leverage paths exist for an engineer trying to break into AI roles. This codebase already proves what it needs to prove.

The brand and domain were portfolio scaffolding. They served their purpose.

## License

No license file. All rights reserved. If you want to reuse pieces, ask.
