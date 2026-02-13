# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Margin Invest is a deterministic investment analysis platform. See `docs/plans/2026-02-12-margin-invest-v1-design.md` for the complete design document.

## Architecture

Monorepo with three packages:
- `engine/` — Pure Python scoring library (zero web dependencies)
- `api/` — FastAPI service wrapping the engine
- `web/` — Next.js 15 frontend

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
uv run pytest engine/tests/ -v              # Engine tests
uv run pytest api/tests/ -v                 # API tests
uv run pytest -v                            # All tests
uv run pytest --cov=margin_engine engine/   # With coverage
```

## Development Services

```bash
docker compose up -d                         # Start PostgreSQL/TimescaleDB + Redis
docker compose down                          # Stop services
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
- No human judgment anywhere in the pipeline
