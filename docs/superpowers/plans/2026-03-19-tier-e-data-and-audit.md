# Tier E Data Endpoints and Audit Plan (E5, E7, E4)

**Goal:** Implement 13F analytics, sector endpoints, and audit backtesting.

**Spec:** `docs/superpowers/specs/2026-03-18-tier-e-known-gaps-design.md` (Tracks B and C)

**Schema note:** E5 replaces 5 schemas in `schemas/thirteenf.py`. Breaking change but safe (old schemas returned empty arrays).

---

## E5: 13F Analytics

### Task 1: Quarter resolution service
- Create: `api/src/margin_api/services/thirteenf_analytics.py`
- [ ] Write tests for resolve_quarter: auto-detect, explicit parsing, <2 quarters -> 404
- [ ] Implement get_available_quarters + resolve_quarter. Format YYYY-QN -> date.
- [ ] Commit: `"feat(13f): implement quarter resolution"`

### Task 2: New positions computation
- Modify: `api/src/margin_api/services/thirteenf_analytics.py`
- [ ] Tests: 3 mgrs AAPL Q2, 1 Q1 -> 2 new positions, sorted desc, limit 50
- [ ] Implement compute_new_positions. Set difference on (manager_id, security_master_id). Join Manager + SecurityMaster.
- [ ] Commit: `"feat(13f): implement new positions logic"`

### Task 3: Crowded trades computation
- Modify: `api/src/margin_api/services/thirteenf_analytics.py`
- [ ] Tests: most holders first, concentration correct, top 20
- [ ] Implement compute_crowded_trades. Count managers per ticker, compute concentration.
- [ ] Commit: `"feat(13f): implement crowded trades logic"`

### Task 4: Update schemas and wire routes
- Modify: `schemas/thirteenf.py`, `routes/thirteenf.py`
- [ ] Tests: endpoints return data, quarter param works, plan gating preserved
- [ ] Update 5 schemas per spec E5
- [ ] Replace stubs, add quarter Query param, preserve require_plan
- [ ] Update frontend types in smart-money components
- [ ] Commit: `"feat(13f): wire analytics, update schemas"`

---

## E7: Sector Endpoints

### Task 5: Verify market_cap wiring
- Audit: `routes/scores.py` response construction
- [ ] Check if market_cap (schema line 165) is populated from AssetProfile
- [ ] Wire if missing (single line change)
- [ ] Test ScoreResponse includes market_cap
- [ ] Commit: `"fix(scores): wire market_cap from AssetProfile"`

### Task 6: Sector list and champion endpoints
- Create: `routes/sectors.py`, `schemas/sectors.py`
- Modify: `services/sector_stats.py`, `app.py`
- [ ] Tests: GET /sectors returns sectors, GET /sectors/{s}/champion returns top ticker, empty -> 404
- [ ] Schemas: SectorSummary and SectorChampionDetail (NOT ChampionResponse, avoids collision)
- [ ] Add query functions to sector_stats.py (published V4Scores joined to Asset)
- [ ] Implement routes with prefix /api/v1/sectors, register in app.py
- [ ] Commit: `"feat(sectors): add sector list and champion endpoints"`

---

## E4: Backtesting Audit

### Task 7: Audit backtesting components
- Audit: `web/src/components/backtesting/*.tsx` (16 files)
- [ ] Grep for mock data: mockData, placeholder, hardcoded, sample, dummy, fake
- [ ] Check each component has loading, error, and empty states
- [ ] Fix gaps with Skeleton or error components
- [ ] Run: `cd web && npx vitest run src/components/backtesting`
- [ ] Commit: `"audit(backtesting): verify no mock data, fix loading/error states"`

---

### Task 8: Final validation
- [ ] `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
- [ ] `uv run ruff check --fix api/ && uv run ruff format api/`
- [ ] `cd web && npx vitest run`
- [ ] Commit any fixes
