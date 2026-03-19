# Tier E Coverage Campaign Plan (E6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Achieve 90% API test coverage (CLAUDE.md target). Systematic audit then prioritized test writing.

**Architecture:** E6 runs LAST, after Plans 1 and 2 complete. Covers all new code from E1-E5 and E7. Phase 1 audits current coverage to determine true scope.

**Tech Stack:** pytest, pytest-asyncio, aiosqlite, fakeredis, pytest-cov

**Spec:** `docs/superpowers/specs/2026-03-18-tier-e-known-gaps-design.md` (Track D)

**Depends on:** Plan 1 (governance chain) and Plan 2 (data endpoints) must be complete first.

---

### Task 1: Coverage audit
- [ ] Run: `uv run pytest api/tests/ --cov=margin_api --cov-report=term-missing --ignore=api/tests/services/test_xbrl_parser.py`
- [ ] Record starting percentage (spec says ~67%, may be stale)
- [ ] Build gap map: modules below 90%, uncovered lines, prioritize by risk
- [ ] Save audit to `docs/superpowers/reports/coverage-audit.md`

### Task 2: P0 tests -- governance workers and circuit breakers
- Create: `api/tests/workers/test_governance_workers.py`
- [ ] stage_scores creates approval, publish_scores requires approval, expire_stale_approvals
- [ ] Circuit breaker with dynamic thresholds from E1
- [ ] Commit: `"test(p0): governance workers and circuit breaker coverage"`

### Task 3: P1 tests -- rarity worker and new feature code
- Expand: `api/tests/workers/test_rarity_worker.py`
- [ ] Rarity: percentile ranking, multi-ticker, regime, edge cases
- [ ] All new code from E1-E5, E7 (config service, webhook dispatcher, 13F analytics, sectors)
- [ ] Commit: `"test(p1): rarity expansion and new feature coverage"`

### Task 4: P2 tests -- route handlers and services
- [ ] Cover route handlers below 90% from gap map
- [ ] Cover uncovered service branches (accumulation, ingest pipeline)
- [ ] Commit: `"test(p2): route handler and service branch coverage"`

### Task 5: P3 tests -- utilities and validation
- [ ] Cover remaining utility functions and schema validation
- [ ] Commit: `"test(p3): utility and validation coverage"`

### Task 6: Final validation
- [ ] Re-run coverage, verify: overall >= 90%, no module below 80%, P0/P1 at 90%+
- [ ] Lint: `uv run ruff check --fix api/ && uv run ruff format api/`
- [ ] Commit: `"test: achieve 90% API coverage target"`
