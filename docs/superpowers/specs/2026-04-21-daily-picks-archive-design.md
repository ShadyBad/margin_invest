# Daily Picks Archive — Design Spec

**Date**: 2026-04-21
**Status**: Draft
**Goal**: Tamper-evident public archive of daily ranked picks, published at every US market close.

## Mission

Every US trading day after market close, freeze the day's conviction-gated picks and publish them to a public, tamper-evident archive. Nobody — including operators — can backdate or modify historical picks. This is the foundation of the track record moat: every day without this live is a day shaved off the eventual provable track record.

## Architecture Overview

The archiver is an ARQ cron job inside the existing `margin_api` package. It reads published V4 scores from the database, generates a deterministic snapshot, computes a SHA-256 hash chain, and publishes to two independent public destinations: a GitHub repository and a Cloudflare R2 bucket.

```
~4:30 PM ET cron (21:30 UTC)
    │
    ├─ Holiday guard (pandas_market_calendars NYSE)
    ├─ Scores-ready guard (published V4Scores for today)
    ├─ Snapshot generation (pure function)
    ├─ Hash computation (input_data_hash → hash_chain → payload_hash)
    ├─ Parallel publish (GitHub + R2, independent failures)
    └─ PostHog alerting on any failure
```

## Module Structure

```
api/src/margin_api/archiver/
├── __init__.py
├── snapshot.py          # Pure function: DB rows → SnapshotPayload
├── hasher.py            # Canonical JSON + SHA-256
├── publishers/
│   ├── __init__.py
│   ├── github.py        # Commit snapshot to ShadyBad/daily-picks
│   └── r2.py            # Upload to Cloudflare R2 public bucket
├── scheduler.py         # Holiday-aware cron guard
├── manifest.py          # Regenerate MANIFEST.md deterministically
└── worker.py            # ARQ task entry point
```

Tests at `api/tests/archiver/` mirror this structure.

## Snapshot Schema (v1.0.0)

```json
{
  "snapshot_version": "1.0.0",
  "snapshot_date": "YYYY-MM-DD",
  "generated_at_utc": "ISO-8601 with microseconds",
  "market_close_time": "ISO-8601",
  "universe_size": "<int: total scored tickers>",
  "methodology_version": "4.0.0",
  "model_hash": "<git commit SHA of margin_invest at build time>",
  "input_data_hash": "<SHA-256 of canonical V4Score batch>",

  "top_picks": [
    {
      "rank": "<int: 1-indexed>",
      "ticker": "<string>",
      "composite_score": "<float>",
      "conviction": "<HIGHEST|HIGH|MODERATE>",
      "opportunity_type": "<compounder|mispricing|both|efficient_growth|neither>",
      "style": "<BLEND|GROWTH|VALUE>",
      "track_scores": {
        "track_a": { "score": "<float>", "qualifies": "<bool>", "gates_passed": "<int>", "total_gates": "<int>" },
        "track_b": { "score": "<float>", "qualifies": "<bool>", "gates_passed": "<int>", "total_gates": "<int>" },
        "track_c": { "score": "<float>", "qualifies": "<bool>", "gates_passed": "<int>", "total_gates": "<int>" }
      },
      "pillars": {
        "<pillar_name>": {
          "factors": {
            "<factor_name>": "<float: percentile score>"
          }
        }
      },
      "modifiers": {
        "liquidity": "<float>",
        "insider_signal": "<float>",
        "inflection": "<float>",
        "tam": "<float>",
        "anti_consensus": "<float>"
      },
      "ml": {
        "alpha": "<float|null>",
        "confidence": "<float|null>",
        "override": "<none|upgrade|downgrade>"
      },
      "sector": "<GICS sector>",
      "market_cap_usd": "<int>",
      "price_at_close": "<float>"
    }
  ],

  "excluded_count": "<int: tickers with LOW or FAILED conviction>",
  "exclusion_summary": {
    "conviction_low": "<int>",
    "conviction_failed": "<int>"
  },

  "hash_chain": {
    "previous_date": "<YYYY-MM-DD|null>",
    "previous_payload_hash": "<hex string|null>"
  },

  "payload_hash": "<SHA-256 of all fields above, computed last>"
}
```

### Schema design decisions

- **Pillar groupings with nested factors**: Individual factor scores are grouped by their pillar (quality, value, momentum, growth, catalyst) using the factor registry's pillar mapping. Only factors that were actually computed for a ticker appear — no nulls, no zeros for missing data.
- **Track scores preserved**: The 3-track cascade system (A=Compounder, B=Mispricing, C=Balanced) is the engine's real output. Published as-is rather than fabricating aggregate scores.
- **Conviction-gated picks**: Only HIGHEST, HIGH, and MODERATE conviction tickers appear in `top_picks`. LOW and FAILED are counted in `excluded_count`/`exclusion_summary`.
- **Ranking**: `top_picks` sorted by `composite_score` descending. Ties broken by ticker alphabetically for stable ordering.

## Hash Provenance Chain

Three hashes create a verifiable chain:

1. **`model_hash`**: Git commit SHA of `margin_invest` at Docker build time. Baked into the container as `MARGIN_GIT_SHA` env var. Proves which version of the scoring code produced these results. Anyone can checkout that SHA and audit the logic.

2. **`input_data_hash`**: SHA-256 of the canonical JSON of the full `V4Score` batch (all rows, all columns including `detail` and track breakdowns, sorted by ticker). Fingerprints the exact database state that produced the snapshot.

3. **`payload_hash`**: SHA-256 of the canonical JSON of the entire snapshot (all fields except `payload_hash` itself). Sorted keys, UTF-8, no whitespace (`separators=(",", ":")`). Computed last.

**Hash chain**: Each snapshot's `hash_chain.previous_payload_hash` references the prior trading day's `payload_hash`, forming a linked chain. The genesis snapshot has `previous_date: null` and `previous_payload_hash: null`.

**Future V2 enhancement**: Persist the full feature matrix at score time for true input provenance. Currently `input_data_hash` fingerprints the scoring output, not the raw input data.

## Data Flow

### Step 1: Schedule guard

ARQ cron fires at 21:30 UTC daily (weekdays only). `scheduler.is_trading_day(date)` checks `pandas_market_calendars` NYSE calendar. Non-trading days (holidays, weekends) log and skip silently.

### Step 2: Scores-ready guard

Query `V4Score` for rows with `published=True` and `scored_at::date = today`. If zero rows, emit PostHog `archiver.scores_not_ready` and exit.

### Step 3: Snapshot generation

`snapshot.generate(date, db_session)` is a pure function (aside from DB reads):

1. Query all published V4Scores for the date, joined with Asset for ticker/sector/market_cap/price.
2. Filter to conviction IN (HIGHEST, HIGH, MODERATE).
3. Extract pillar factor scores from `V4Score.detail` JSON column (contains `quality`, `value`, `momentum`, `growth` sub-objects, each with `name`, `raw_value`, `percentile_rank` per factor). Reorganize by pillar. Note: `detail` must be non-null — scores with null detail are excluded with a warning.
4. Sort by composite_score DESC, assign 1-indexed ranks.
5. Count excluded tickers by conviction level.
6. Return `SnapshotPayload` (Pydantic model).

### Step 4: Hash computation

`hasher.compute_hashes(payload, previous_snapshot)`:

1. Compute `input_data_hash` from the raw V4Score batch.
2. Set `hash_chain` from previous snapshot's `payload_hash` (fetched from GitHub, R2 fallback).
3. Compute `payload_hash` over the full snapshot.

### Step 5: Parallel publish

`asyncio.gather()` runs GitHub and R2 publishers concurrently with `return_exceptions=True`. Each publisher succeeds or fails independently.

### Step 6: Alerting

PostHog events emitted based on outcome (see Failure Taxonomy below).

## Publishers

### GitHub Publisher (`publishers/github.py`)

**Target repo**: `ShadyBad/daily-picks` (configurable via `ARCHIVE_GITHUB_REPO`).

**Repo structure**:
```
daily-picks/
├── README.md              # Archive format docs + verification snippet
├── MANIFEST.md            # Human-readable running index
├── manifest.json          # Machine-readable index
├── snapshots/
│   └── YYYY/
│       └── MM/
│           └── DD.json
└── verify.py              # Standalone verification script
```

**Commit convention**: `snapshot: YYYY-MM-DD (N picks, hash: abcd1234...)`. Single atomic commit containing the snapshot JSON + both MANIFEST files.

**Idempotency**: GET file at `snapshots/YYYY/MM/DD.json` before creating. If exists with matching `payload_hash`, skip. If exists with different hash, emit `archiver.hash_mismatch` (critical) and abort.

**Auth**: Fine-grained PAT in `ARCHIVE_GITHUB_TOKEN`, scoped to `ShadyBad/daily-picks` with `contents: write`.

### R2 Publisher (`publishers/r2.py`)

**Bucket structure**:
```
snapshots/YYYY/MM/DD.json
snapshots/YYYY/MM/DD.json.sha256   # Hex digest for curl-based verification
manifest.json
```

**Auth**: `ARCHIVE_R2_ACCESS_KEY_ID`, `ARCHIVE_R2_SECRET_ACCESS_KEY`, `ARCHIVE_R2_BUCKET`, `ARCHIVE_R2_ENDPOINT` in Railway env. Uses `boto3` with S3-compatible endpoint.

**Public access**: R2 bucket with public read enabled (Cloudflare dashboard setting). `pub-<hash>.r2.dev` URL for V1.

### MANIFEST Generation (`manifest.py`)

**Deterministic**: Fully regenerated from the snapshot list on every run — never appended to. Same input list produces byte-identical output.

**MANIFEST.md** (human-readable):
```markdown
# Margin Invest Daily Picks Archive

| Date | Picks | Top Pick | Payload Hash | Chain |
|------|-------|----------|-------------|-------|
| 2026-04-21 | 14 | AAPL (87.3) | `c7d4e8f1...` | <- `f9e2a1b3...` |
| 2026-04-18 | 12 | MSFT (85.1) | `f9e2a1b3...` | <- `(genesis)` |
```

Includes verification instructions and a 3-line Python snippet at the top.

**manifest.json** (machine-readable): Array of `{ date, picks_count, top_ticker, top_score, payload_hash, previous_hash }` sorted newest-first.

### verify.py (shipped in public repo)

```python
#!/usr/bin/env python3
"""Verify any Margin Invest daily snapshot. Usage: python verify.py snapshots/2026/04/21.json"""
import hashlib, json, sys
snapshot = json.load(open(sys.argv[1]))
payload_hash = snapshot.pop("payload_hash")
canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
computed = hashlib.sha256(canonical).hexdigest()
print(f"{'VALID' if computed == payload_hash else 'INVALID'}: {computed}")
```

## Scheduling

**Cron**: 21:30 UTC weekdays (ARQ cron entry). During EDT (March–November) this is 5:30 PM ET. During EST (November–March) this is 4:30 PM ET — 15 minutes after the 4:15 target. Both are after market close year-round. The EDT run is slightly later than ideal (75 min after close) but acceptable — the scores are already published by then.

**Holiday detection**: `pandas_market_calendars` NYSE calendar. `is_trading_day(date)` returns False for market holidays, weekends.

## Failure Taxonomy

| Failure | Detection | Response | PostHog Event | Severity |
|---|---|---|---|---|
| Not a trading day | NYSE calendar | Log, skip | None | — |
| Scores not published | Zero published V4Scores for today | Skip | `archiver.scores_not_ready` | warning |
| Snapshot generation error | Exception in `snapshot.generate()` | Abort | `archiver.generation_failed` | critical |
| GitHub publish fails | GitHub API exception | R2 still publishes | `archiver.github_failed` | warning |
| R2 publish fails | boto3 exception | GitHub still publishes | `archiver.r2_failed` | warning |
| Both publishers fail | Both exceptions | Abort | `archiver.publish_failed` | critical |
| Hash mismatch (idempotency) | Existing file has different hash | Abort, investigate | `archiver.hash_mismatch` | critical |
| Chain break | Can't fetch previous snapshot | Publish with null chain, flag | `archiver.chain_break` | warning |

**No automatic retries**: For a tamper-evident system, silent retries that might publish slightly different data are worse than a loud failure. Manual re-run via CLI:

```bash
uv run python -m margin_api.cli archive --date 2026-04-21
```

## PostHog Integration

All events use `posthog.capture()` with the existing client from `margin_api`. Properties include:

```python
{
    "severity": "warning|critical",
    "date": "2026-04-21",
    "error_message": "...",
    "traceback": "...",        # if applicable
    "github_published": True,  # bool
    "r2_published": False,     # bool
    "picks_count": 14,         # if snapshot was generated
    "payload_hash": "..."      # if snapshot was generated
}
```

## Configuration (Environment Variables)

| Variable | Description | Required |
|---|---|---|
| `ARCHIVE_GITHUB_TOKEN` | Fine-grained PAT for `ShadyBad/daily-picks` | Yes |
| `ARCHIVE_GITHUB_REPO` | Target repo (default: `ShadyBad/daily-picks`) | No |
| `ARCHIVE_R2_ACCESS_KEY_ID` | Cloudflare R2 access key | Yes |
| `ARCHIVE_R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key | Yes |
| `ARCHIVE_R2_BUCKET` | R2 bucket name | Yes |
| `ARCHIVE_R2_ENDPOINT` | R2 S3-compatible endpoint URL | Yes |
| `MARGIN_GIT_SHA` | Git commit SHA, baked into Docker build | Yes |

## Testing Strategy

### Test files

```
api/tests/archiver/
├── conftest.py           # Shared fixtures: frozen V4Score rows, mock Assets
├── test_snapshot.py      # Pure function tests (target: >=95%)
├── test_hasher.py        # Canonical JSON determinism (target: >=95%)
├── test_manifest.py      # Deterministic regeneration
├── test_scheduler.py     # Holiday detection, DST edge cases
├── test_github.py        # GitHub publisher with mocked API
├── test_r2.py            # R2 publisher with mocked boto3
└── test_worker.py        # End-to-end orchestration
```

### Key test cases

**snapshot.py** (>=95% coverage):
- Golden-value test: frozen V4Score + Asset rows → expected SnapshotPayload, every field asserted.
- Conviction gating: all 5 levels in, only 3 in `top_picks`.
- Ranking: ties broken by ticker alphabetically.
- Missing factors: sparse data → pillar has fewer factors, no nulls.
- Empty universe: no published scores → returns None.

**hasher.py** (>=95% coverage):
- Determinism: same payload → same hash, 100 iterations.
- Sort-key correctness: unordered keys → sorted canonical JSON.
- No-whitespace: `separators=(",", ":")` enforced.
- Hash chain: changing previous hash changes payload hash.

**manifest.py**:
- Idempotent: generate twice from same list → byte-identical.
- Ordering: random input order → newest-first output.
- Genesis: single snapshot with null previous → correct rendering.

**scheduler.py**:
- Known holidays (MLK Day, Good Friday, Independence Day observed) → False.
- Normal weekday → True. Weekend → False.

**publishers (github.py, r2.py)**:
- Happy path with mocked HTTP/boto3.
- Idempotent: file exists with same hash → skip.
- Hash mismatch: file exists with different hash → raise.
- Network failure: 500 → raises for caller to handle.

**worker.py** (end-to-end):
- Full success, partial failure (one publisher), not a trading day, scores not ready, idempotent re-run.

### CI (`.github/workflows/archiver-ci.yml`)

Triggers on PRs touching `api/src/margin_api/archiver/**` or `api/tests/archiver/**`:
- `ruff check` + `ruff format --check`
- `mypy --strict`
- `pytest --cov=margin_api.archiver --cov-fail-under=90`

## Acceptance Criteria

- [ ] End-to-end test: generate snapshot for a frozen test date, publish to a test repo, verify hash chain
- [ ] Idempotency: running twice on the same date produces no duplicate commits
- [ ] Independent failure: GitHub failure doesn't block R2, and vice versa — PostHog alerts emitted
- [ ] MANIFEST.md regenerates deterministically: running twice produces byte-identical output
- [ ] `mypy --strict` passes with zero errors on `api/src/margin_api/archiver/`
- [ ] `ruff` passes with zero warnings on `api/src/margin_api/archiver/`
- [ ] Test coverage >= 90% on `snapshot.py` and `hasher.py`
- [ ] CLI command `archive --date` works for manual re-runs

## Non-Goals

- Performance tracking vs SPY (separate project)
- Public website for browsing the archive (separate project)
- Email/push notifications (separate project)
- Historical backfill — only publish from today forward. Backfilled data is worthless for trust.
- True feature-matrix input hashing (V2 enhancement)

## Dependencies

New Python packages:
- `pandas_market_calendars` — NYSE holiday calendar
- `boto3` — S3-compatible R2 uploads

Existing packages (already in the project):
- `httpx` — GitHub API calls (async)
- `posthog` — event capture
- `pydantic` — snapshot schema
