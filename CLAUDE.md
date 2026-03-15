# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Margin Invest is a deterministic investment analysis platform. See `docs/plans/2026-02-12-margin-invest-v1-design.md` for the complete design document.

## Architecture

Monorepo with three packages:
- `engine/` — Pure Python scoring library (zero web dependencies)
- `api/` — FastAPI service wrapping the engine (FastAPI + SQLAlchemy 2.0 + asyncpg)
- `web/` — Next.js 16 frontend (React 19, Tailwind v4, Vitest)

Supporting infrastructure:
- **DB**: PostgreSQL 16 (local Homebrew on port 5432, role `margin`/`margin_dev`/`margin_invest`)
- **Cache**: Redis (via Docker or local)
- **Workers**: ARQ (async Redis queue) — 18 registered functions, 7 cron jobs
- **Migrations**: Alembic (in `api/alembic/`)

## Package Management

Use **uv** for all Python project and package management:

```bash
uv add <package> --package margin-engine    # Add to engine
uv add <package> --package margin-api       # Add to api
uv sync                                      # Sync all workspace members
uv run <command>                             # Run in virtual environment
```

Use **context7 MCP** to look up documentation for libraries and frameworks before implementing solutions.

## Running Tests

```bash
uv run pytest engine/tests/ -v              # Engine tests (~2621 tests)
uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py  # API tests (~1587)
cd web && npx vitest run                    # Web tests (~1285 tests)
uv run pytest -v                            # All Python tests
uv run pytest --cov=margin_engine engine/   # With coverage
```

## Linting

```bash
uv run ruff check --fix .                   # Python lint + autofix
uv run ruff format .                        # Python format
cd web && npx eslint --fix .                # TypeScript/JSX lint
```

## CLI Commands

```bash
uv run python -m margin_api.cli seed --tickers AAPL MSFT        # Seed asset data
uv run python -m margin_api.cli score --tickers AAPL MSFT       # Score assets
uv run python -m margin_api.cli edgar-backfill --start-year 2009 # Backfill EDGAR filings
uv run python -m margin_api.cli price-backfill --start-date 2009-01-01  # Backfill prices
```

## Development Services

```bash
docker compose up -d                         # Start Redis (PostgreSQL runs via local Homebrew)
docker compose down                          # Stop services
uvicorn margin_api.app:create_app --factory --reload  # Run API server (no module-level app var)
```

## Python Version

Python 3.13.5+ (specified in `.python-version`).

## Code Standards

- **TDD**: Write failing test first, then implement. No scoring formula ships without a golden-value test.
- **Coverage**: engine/ ≥ 95%, api/ ≥ 90%, web/ ≥ 80%
- **Formatting**: Ruff (line length 100)
- **Types**: All public functions must have type annotations
- **Models**: Use Pydantic for all data models
- **Determinism**: Same inputs must produce same outputs. AI calls use temperature=0.

## Key Design Principles

- Elimination filters run BEFORE scoring (fail-fast)
- All scoring uses percentile ranks (0-100) for cross-factor comparison
- Sector-neutral scoring: rank within GICS sector first, then combine
- Growth stage determines factor weight adjustments
- Cyclical assets use 7-year median normalization
- Human oversight via staged → approved → published pipeline (scores and ML models require approval)

## Deployment

- **Railway**: Auto-deploys on push to main. Two services: `margin_invest` (API) and `margin-worker` (ARQ)
- **Dockerfile**: `api/Dockerfile` — runs `alembic upgrade head` before `uvicorn` (migrations must succeed or API won't start)
- **Containers are ephemeral**: Never store artifacts on filesystem — use DB (LargeBinary) or object storage

## Alembic Migrations

```bash
uv run alembic revision --autogenerate -m "description"  # Create migration
uv run alembic upgrade head                               # Apply migrations
uv run alembic heads                                      # Check for multiple heads (fix before merging)
```

- Always use idempotent checks (`inspector.has_table()`, `if col not in existing`) — same migration may run on multiple containers
- New ORM model = new migration. Don't assume tables exist.

## Gotchas

- **DateTime columns**: Must use `DateTime(timezone=True)` — asyncpg is strict about tz-aware vs naive. Defaults: `datetime.now(UTC)`
- **JSONVariant**: Use `JSON().with_variant(JSONB(), "postgresql")` for SQLite test compatibility
- **yfinance NaN**: Raw financial data contains NaN floats — sanitize with `_sanitize_for_json()` before storing as JSONB
- **Computed properties**: `CompositeScore.composite_tier`, `.signal`, `FactorBreakdown.average_percentile`, `FilterResult.verdict` are `@property` — not in `model_dump()`. Must populate manually when reconstructing from JSONB
- **Signal renames**: "buy"→"strong", "hold"→"stable", "watch"→"emerging", "sell"→"weak", "urgent_sell"→"failed". DB columns still store old values in existing rows
- **CompositeTier**: Renamed from `ConvictionLevel` — backward-compat alias exists. API field: `composite_tier`. DB column names unchanged
- **Broken test**: `test_xbrl_parser.py` must be `--ignore`d (E501 issues, exempt in pyproject.toml)
