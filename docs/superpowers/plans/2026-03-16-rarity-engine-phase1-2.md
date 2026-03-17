# Rarity Engine Implementation Plan (Phases 1-2)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the rarity engine's core computation, all 6 signals, API endpoints, and pipeline integration as a parallel sidecar to the existing v4 scoring pipeline.

**Architecture:** Pure-engine computation modules in `engine/src/margin_engine/rarity/` compute 6 rarity signals from the factor matrix stored in `V4Score.detail` JSONB. A new `compute_rarity` ARQ worker runs in parallel with `stage_scores` (not inline), writing results to new `rarity_scores` and `rarity_distribution_snapshots` tables. Two new API endpoints expose rarity data. The existing scoring pipeline is untouched except for a 3-line enqueue addition.

**Tech Stack:** Python 3.13, Pydantic v2, numpy, SQLAlchemy 2.0 (async), FastAPI, ARQ, FRED API, yfinance, pytest + aiosqlite (tests)

**Spec:** `docs/superpowers/specs/2026-03-16-rarity-engine-design.md`

---

## File Map

### New Files (Engine)
| File | Responsibility |
|------|---------------|
| `engine/src/margin_engine/rarity/__init__.py` | Module exports |
| `engine/src/margin_engine/rarity/models.py` | `RarityResult`, `RarityConfig`, `RarityRegime` Pydantic models |
| `engine/src/margin_engine/rarity/convergence.py` | `compute_convergence()` — pillar alignment scoring |
| `engine/src/margin_engine/rarity/joint_rarity.py` | `compute_joint_rarity()` — empirical joint CDF |
| `engine/src/margin_engine/rarity/combination_signature.py` | `build_signature()` — human-readable factor fingerprint |
| `engine/src/margin_engine/rarity/quality_momentum.py` | `compute_quality_momentum()` — temporal trajectory |
| `engine/src/margin_engine/rarity/smart_money.py` | `compute_smart_money_convergence()` — institutional + insider |
| `engine/src/margin_engine/rarity/regime.py` | `classify_regime()`, `compute_regime_alignment()` |
| `engine/src/margin_engine/rarity/historical_rarity.py` | `compute_historical_frequency()` — accumulating baseline |
| `engine/src/margin_engine/rarity/pillar_extraction.py` | `extract_pillar_percentiles()` — Track A/B pillar logic |
| `engine/src/margin_engine/rarity/rarity_engine.py` | `compute_rarity_scores()` — orchestrator |

### New Files (Engine Tests)
| File | Responsibility |
|------|---------------|
| `engine/tests/rarity/__init__.py` | Test package |
| `engine/tests/rarity/test_convergence.py` | Golden-value convergence tests |
| `engine/tests/rarity/test_joint_rarity.py` | Golden-value joint CDF tests |
| `engine/tests/rarity/test_combination_signature.py` | Signature format tests |
| `engine/tests/rarity/test_pillar_extraction.py` | Track A/B extraction tests |
| `engine/tests/rarity/test_quality_momentum.py` | Quality momentum tests |
| `engine/tests/rarity/test_smart_money.py` | Smart money convergence tests |
| `engine/tests/rarity/test_regime.py` | Regime classification tests |
| `engine/tests/rarity/test_historical_rarity.py` | Historical frequency tests |
| `engine/tests/rarity/test_rarity_engine.py` | Orchestrator integration tests |

### New Files (API)
| File | Responsibility |
|------|---------------|
| `api/src/margin_api/routes/rarity.py` | `GET /api/v1/rarity/{ticker}`, `GET /api/v1/rarity/picks` |
| `api/src/margin_api/schemas/rarity.py` | `RarityResponse`, `RarityPicksResponse` |
| `api/tests/test_rarity_routes.py` | API endpoint tests |

### Modified Files
| File | Change |
|------|--------|
| `engine/src/margin_engine/models/scoring.py:85` | Add `metadata: dict[str, Any] \| None = None` to `FactorScore` |
| `api/src/margin_api/db/models.py:1184` | Add `RarityScore` and `RarityDistributionSnapshot` ORM models |
| `api/src/margin_api/workers.py:784-796` | Add `compute_rarity` enqueue in `full_score_v4` |
| `api/src/margin_api/workers.py:3757-3787` | Register `compute_rarity` in `WorkerSettings.functions` |
| `api/src/margin_api/schemas/scores.py:170-173` | Add rarity fields to `ScoreResponse` |
| `api/src/margin_api/app.py:37,165` | Import and register rarity router |
| `api/src/margin_api/data/fred_client.py` | Rename to `macro_data_client.py`, add yield curve + credit spread + VIX |
| `api/src/margin_api/cli.py` | Update `fred_client` import to `macro_data_client` |
| `engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py` | Populate `FactorScore.metadata` |
| `engine/src/margin_engine/scoring/quantitative/insider_cluster.py` | Populate `FactorScore.metadata` |

---

## Task 1: FactorScore.metadata Field + Pillar Extraction

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:78-93`
- Create: `engine/src/margin_engine/rarity/__init__.py`
- Create: `engine/src/margin_engine/rarity/pillar_extraction.py`
- Test: `engine/tests/rarity/__init__.py`
- Test: `engine/tests/rarity/test_pillar_extraction.py`

- [ ] **Step 1: Create test directory and write pillar extraction tests**

```python
# engine/tests/rarity/__init__.py
# (empty)

# engine/tests/rarity/test_pillar_extraction.py
"""Tests for Track A / Track B pillar extraction logic."""

from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore

from margin_engine.rarity.pillar_extraction import extract_pillar_percentiles


def _fb(name: str, pctl: float, weight: float = 0.25) -> FactorBreakdown:
    """Helper: create a FactorBreakdown with one sub-score at the given percentile."""
    return FactorBreakdown(
        factor_name=name,
        weight=weight,
        sub_scores=[FactorScore(name=f"{name}_main", raw_value=1.0, percentile_rank=pctl)],
    )


def _make_composite(
    ticker: str = "TEST",
    q: float = 80.0,
    v: float = 75.0,
    m: float = 70.0,
    g: float | None = 65.0,
    catalyst: float | None = None,
    winning_track: str = "compounder",
) -> CompositeScore:
    growth = _fb("growth", g) if g is not None else None
    cat = _fb("catalyst", catalyst) if catalyst is not None else None
    # Track B: momentum is a dummy (weight=0, no sub_scores)
    mom = _fb("momentum", m) if winning_track != "mispricing" else FactorBreakdown(
        factor_name="momentum", weight=0.0, sub_scores=[]
    )
    return CompositeScore(
        ticker=ticker,
        composite_percentile=75.0,
        composite_raw_score=75.0,
        quality=_fb("quality", q),
        value=_fb("value", v),
        momentum=mom,
        growth=growth,
        catalyst=cat,
        filters_passed=[],
        data_coverage=0.9,
        winning_track=winning_track,
    )


def test_track_a_returns_four_pillars():
    cs = _make_composite(q=92, v=85, m=78, g=88)
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 92.0, "value": 85.0, "momentum": 78.0, "growth": 88.0}


def test_track_b_returns_three_pillars_with_catalyst():
    cs = _make_composite(q=90, v=82, g=None, catalyst=75, winning_track="mispricing")
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 90.0, "value": 82.0, "catalyst": 75.0}
    assert "momentum" not in pillars
    assert "growth" not in pillars


def test_track_a_no_growth_returns_three_pillars():
    cs = _make_composite(q=80, v=70, m=60, g=None)
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 80.0, "value": 70.0, "momentum": 60.0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_pillar_extraction.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.rarity'`

- [ ] **Step 3: Add `metadata` field to FactorScore and create pillar extraction**

In `engine/src/margin_engine/models/scoring.py`, add to imports:
```python
from typing import Any
```

Add field to `FactorScore` class (after `stub: bool = False`):
```python
    metadata: dict[str, Any] | None = None  # Intermediate signals for enrichment layers
```

Create `engine/src/margin_engine/rarity/__init__.py`:
```python
"""Rarity Engine — once-in-a-generation opportunity detection."""
```

Create `engine/src/margin_engine/rarity/pillar_extraction.py`:
```python
"""Extract meaningful pillar percentiles from a CompositeScore.

Track A (compounder): quality, value, momentum, growth (4 pillars)
Track B (mispricing): quality, value, catalyst (3 pillars — dummy momentum excluded)
"""

from __future__ import annotations

from margin_engine.models.scoring import CompositeScore


def extract_pillar_percentiles(composite: CompositeScore) -> dict[str, float]:
    """Return {pillar_name: average_percentile} for meaningful pillars only.

    Track B stocks have momentum as a dummy FactorBreakdown (weight=0.0,
    sub_scores=[]) which returns average_percentile=0.0. We detect this
    and exclude it, substituting catalyst if available.
    """
    pillars: dict[str, float] = {}

    pillars["quality"] = composite.quality.average_percentile
    pillars["value"] = composite.value.average_percentile

    # Momentum: include only if it has real sub_scores (not Track B dummy)
    if composite.momentum.sub_scores:
        pillars["momentum"] = composite.momentum.average_percentile

    # Growth: include if present
    if composite.growth is not None:
        pillars["growth"] = composite.growth.average_percentile

    # Catalyst: include for Track B (when momentum is dummy)
    if not composite.momentum.sub_scores and composite.catalyst is not None:
        pillars["catalyst"] = composite.catalyst.average_percentile

    return pillars
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_pillar_extraction.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py \
       engine/src/margin_engine/rarity/__init__.py \
       engine/src/margin_engine/rarity/pillar_extraction.py \
       engine/tests/rarity/__init__.py \
       engine/tests/rarity/test_pillar_extraction.py
git commit -m "feat(rarity): add FactorScore.metadata field and pillar extraction"
```

---

## Task 2: Convergence Signal

**Files:**
- Create: `engine/src/margin_engine/rarity/convergence.py`
- Test: `engine/tests/rarity/test_convergence.py`

- [ ] **Step 1: Write convergence golden-value tests**

```python
# engine/tests/rarity/test_convergence.py
"""Golden-value tests for cross-factor convergence scoring."""

from margin_engine.rarity.convergence import compute_convergence


def test_perfect_high_convergence():
    # All pillars at 90 — perfect alignment at high level
    result = compute_convergence([90.0, 90.0, 90.0, 90.0])
    # ratio=1.0, floor_penalty=(90-60)/40=0.75, convergence=75.0
    assert result == 75.0


def test_divergent_profile():
    # Q=95, V=45, M=90, G=50 — split decision
    result = compute_convergence([95.0, 45.0, 90.0, 50.0])
    # floor=45, ceiling=95, ratio=45/95≈0.4737
    # floor_penalty=max(0,(45-60)/40)=0 (below 60 cutoff)
    # convergence=0.4737*0*100=0.0
    assert result == 0.0


def test_moderate_convergence():
    # Q=85, V=80, M=75, G=82
    result = compute_convergence([85.0, 80.0, 75.0, 82.0])
    # floor=75, ceiling=85, ratio=75/85≈0.8824
    # floor_penalty=(75-60)/40=0.375
    # convergence=0.8824*0.375*100≈33.09
    assert result == 33.09


def test_three_pillars_track_b():
    # Track B: quality=88, value=84, catalyst=80
    result = compute_convergence([88.0, 84.0, 80.0])
    # floor=80, ceiling=88, ratio=80/88≈0.9091
    # floor_penalty=(80-60)/40=0.5
    # convergence=0.9091*0.5*100≈45.45
    assert result == 45.45


def test_all_zeros_returns_zero():
    result = compute_convergence([0.0, 0.0, 0.0, 0.0])
    assert result == 0.0


def test_single_pillar():
    # Edge case: one pillar
    result = compute_convergence([85.0])
    # ratio=1.0, floor_penalty=(85-60)/40=0.625
    assert result == 62.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_convergence.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement convergence**

```python
# engine/src/margin_engine/rarity/convergence.py
"""Cross-factor convergence scoring.

Measures how aligned pillar percentiles are at HIGH levels.
Convergence on mediocrity (below 60th percentile) scores zero.
"""

from __future__ import annotations


def compute_convergence(pillar_percentiles: list[float]) -> float:
    """Score 0-100 measuring pillar alignment at high levels.

    Algorithm:
    1. min/max ratio (1.0 = perfectly aligned, 0 = divergent)
    2. Floor penalty ramp: 0 at 60th pctl, 1.0 at 100th
    3. Product scaled to 0-100
    """
    if not pillar_percentiles:
        return 0.0

    floor = min(pillar_percentiles)
    ceiling = max(pillar_percentiles)
    ratio = floor / ceiling if ceiling > 0 else 0.0

    # Below 60th pctl = zero credit. Ramps linearly to 1.0 at 100th.
    floor_penalty = max(0.0, (floor - 60) / 40)

    convergence = ratio * floor_penalty * 100
    return round(convergence, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_convergence.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/convergence.py \
       engine/tests/rarity/test_convergence.py
git commit -m "feat(rarity): add cross-factor convergence signal"
```

---

## Task 3: Joint Rarity Signal

**Files:**
- Create: `engine/src/margin_engine/rarity/joint_rarity.py`
- Test: `engine/tests/rarity/test_joint_rarity.py`

- [ ] **Step 1: Write joint rarity tests**

```python
# engine/tests/rarity/test_joint_rarity.py
"""Golden-value tests for empirical joint CDF rarity computation."""

import numpy as np

from margin_engine.rarity.joint_rarity import compute_joint_rarity, compute_all_joint_rarities


def test_unique_best_stock():
    # Stock 0 dominates on all dimensions — nobody else >= it on all factors
    matrix = np.array([
        [95.0, 90.0, 88.0, 92.0],  # stock 0: best on all
        [70.0, 65.0, 60.0, 55.0],  # stock 1
        [80.0, 75.0, 70.0, 65.0],  # stock 2
    ])
    rarity = compute_joint_rarity(matrix, target_idx=0)
    # Only stock 0 itself dominates (1/3 ≈ 0.333)
    # rarity = (1 - 0.333) * 100 = 66.67
    assert rarity == 66.67


def test_worst_stock_has_low_rarity():
    matrix = np.array([
        [95.0, 90.0, 88.0, 92.0],
        [70.0, 65.0, 60.0, 55.0],  # worst
        [80.0, 75.0, 70.0, 65.0],
    ])
    rarity = compute_joint_rarity(matrix, target_idx=1)
    # All 3 stocks dominate stock 1 (all have >= on every dim)
    # rarity = (1 - 1.0) * 100 = 0.0
    assert rarity == 0.0


def test_all_identical_stocks():
    matrix = np.array([
        [80.0, 75.0, 70.0, 65.0],
        [80.0, 75.0, 70.0, 65.0],
        [80.0, 75.0, 70.0, 65.0],
    ])
    rarity = compute_joint_rarity(matrix, target_idx=0)
    # Every stock dominates (3/3 = 1.0), rarity = 0
    assert rarity == 0.0


def test_compute_all_returns_correct_length():
    matrix = np.array([
        [95.0, 90.0],
        [70.0, 65.0],
        [80.0, 75.0],
        [60.0, 85.0],
    ])
    rarities = compute_all_joint_rarities(matrix)
    assert len(rarities) == 4
    assert all(0 <= r <= 100 for r in rarities)


def test_masked_nan_columns():
    # Stock 2 is Track B: column 3 is NaN (growth missing)
    matrix = np.array([
        [95.0, 90.0, 88.0, 92.0],
        [80.0, 75.0, 70.0, 65.0],
        [85.0, 80.0, 75.0, float("nan")],  # Track B
    ])
    rarity = compute_joint_rarity(matrix, target_idx=2)
    # For stock 2, only compare columns 0-2 (non-NaN)
    # Stock 0 has [95,90,88] >= [85,80,75] on cols 0-2: yes
    # Stock 1 has [80,75,70] >= [85,80,75] on cols 0-2: no (80<85, 75<80, 70<75)
    # Stock 2 has [85,80,75] >= [85,80,75]: yes
    # dominated = 2/3, rarity = (1 - 2/3)*100 = 33.33
    assert rarity == 33.33
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_joint_rarity.py -v`
Expected: FAIL

- [ ] **Step 3: Implement joint rarity**

```python
# engine/src/margin_engine/rarity/joint_rarity.py
"""Empirical joint CDF computation for factor rarity.

Measures how rare a stock's factor combination is by counting what
fraction of the universe has ALL factor percentiles simultaneously
>= the target's percentiles.
"""

from __future__ import annotations

import numpy as np


def compute_joint_rarity(
    factor_matrix: np.ndarray,
    target_idx: int,
) -> float:
    """Compute rarity percentile for a single stock.

    For the target stock, count what fraction of the universe dominates
    it on ALL non-NaN dimensions simultaneously.

    Returns 0-100 (higher = rarer combination).
    """
    target = factor_matrix[target_idx]
    nan_mask = np.isnan(target)

    if nan_mask.all():
        return 0.0

    # Compare only non-NaN columns
    if nan_mask.any():
        valid_cols = ~nan_mask
        comparison = factor_matrix[:, valid_cols] >= target[valid_cols]
    else:
        comparison = factor_matrix >= target

    dominated = comparison.all(axis=1)
    frac_dominating = dominated.sum() / len(factor_matrix)
    return round((1 - frac_dominating) * 100, 2)


def compute_all_joint_rarities(factor_matrix: np.ndarray) -> list[float]:
    """Compute joint rarity for every stock in the matrix.

    Returns a list of rarity percentiles (0-100), one per row.
    """
    return [
        compute_joint_rarity(factor_matrix, i)
        for i in range(len(factor_matrix))
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_joint_rarity.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/joint_rarity.py \
       engine/tests/rarity/test_joint_rarity.py
git commit -m "feat(rarity): add empirical joint CDF rarity signal"
```

---

## Task 4: Combination Signature

**Files:**
- Create: `engine/src/margin_engine/rarity/combination_signature.py`
- Test: `engine/tests/rarity/test_combination_signature.py`

- [ ] **Step 1: Write signature tests**

```python
# engine/tests/rarity/test_combination_signature.py
"""Tests for human-readable combination signature generation."""

from margin_engine.rarity.combination_signature import build_signature


def test_track_a_signature():
    pillars = {"quality": 92.3, "value": 85.7, "momentum": 78.1, "growth": 88.4}
    sig = build_signature(pillars)
    assert sig == "Q90+V85+M80+G90"


def test_track_b_signature():
    pillars = {"quality": 87.0, "value": 73.5, "catalyst": 81.2}
    sig = build_signature(pillars)
    assert sig == "Q85+V75+Cat80"


def test_rounds_to_nearest_5():
    pillars = {"quality": 62.0, "value": 68.0, "momentum": 53.0, "growth": 47.0}
    sig = build_signature(pillars)
    assert sig == "Q60+V70+M55+G45"


def test_boundary_rounding():
    # 72.5/5=14.5 → int(round(14.5))=14 (banker's) → 70; 77.4/5=15.48 → 15 → 75
    pillars = {"quality": 72.5, "value": 77.4}
    sig = build_signature(pillars)
    assert sig == "Q70+V75"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_combination_signature.py -v`
Expected: FAIL

- [ ] **Step 3: Implement signature builder**

```python
# engine/src/margin_engine/rarity/combination_signature.py
"""Human-readable factor fingerprint.

Buckets pillar percentiles to nearest 5 and produces a compact string
like "Q90+V85+M80+G75" for display and historical matching.
"""

from __future__ import annotations

_PILLAR_ABBREV: dict[str, str] = {
    "quality": "Q",
    "value": "V",
    "momentum": "M",
    "growth": "G",
    "catalyst": "Cat",
    "capital_allocation": "CA",
}

# Canonical display order
_PILLAR_ORDER = ["quality", "value", "momentum", "growth", "catalyst", "capital_allocation"]


def _bucket(pctl: float) -> int:
    """Round percentile to nearest 5."""
    return int(round(pctl / 5) * 5)


def build_signature(pillars: dict[str, float]) -> str:
    """Build a compact signature string from pillar percentiles.

    Example: {"quality": 92.3, "value": 85.7, "momentum": 78.1, "growth": 88.4}
    Returns: "Q90+V85+M80+G90"
    """
    parts: list[str] = []
    for name in _PILLAR_ORDER:
        if name in pillars:
            abbrev = _PILLAR_ABBREV.get(name, name[0].upper())
            parts.append(f"{abbrev}{_bucket(pillars[name])}")
    return "+".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_combination_signature.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/combination_signature.py \
       engine/tests/rarity/test_combination_signature.py
git commit -m "feat(rarity): add combination signature fingerprinting"
```

---

## Task 5: Rarity Models (Pydantic)

**Files:**
- Create: `engine/src/margin_engine/rarity/models.py`

- [ ] **Step 1: Create Pydantic models**

```python
# engine/src/margin_engine/rarity/models.py
"""Pydantic models for rarity engine inputs and outputs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RarityRegime(StrEnum):
    EXPANSION = "expansion"
    LATE_CYCLE = "late_cycle"
    CONTRACTION = "contraction"
    CRISIS = "crisis"


class RarityConfig(BaseModel):
    """Tunable weights and thresholds for rarity scoring."""

    # Signal weights (must sum to 1.0)
    joint_rarity_weight: float = 0.35
    convergence_weight: float = 0.25
    historical_rarity_weight: float = 0.15
    quality_momentum_weight: float = 0.10
    smart_money_weight: float = 0.10
    regime_alignment_weight: float = 0.05

    # Gate thresholds
    min_pillar_pctl: float = 60.0
    convergence_gate: float = 50.0
    rarity_score_gate: float = 80.0
    hard_cap: int = 30
    sector_cap_pct: float = 0.40

    # Generational thresholds
    generational_joint_rarity_pctl: float = 97.0
    generational_composite_raw: float = 76.0
    generational_hist_freq: float = 0.02


class RarityDimensionScores(BaseModel):
    """Individual dimension scores that compose the rarity score."""

    joint_rarity_pctl: float = Field(ge=0.0, le=100.0)
    convergence_score: float = Field(ge=0.0, le=100.0)
    historical_frequency: float = Field(ge=0.0, le=100.0, default=50.0)
    quality_momentum: float = Field(ge=0.0, le=100.0, default=50.0)
    smart_money_score: float = Field(ge=0.0, le=100.0, default=50.0)
    regime_alignment: float = Field(ge=0.0, le=100.0, default=50.0)


class RarityResult(BaseModel):
    """Complete rarity assessment for a single ticker."""

    ticker: str
    rarity_score: float = Field(ge=0.0, le=100.0)
    conviction_score: float = Field(ge=0.0, le=100.0, default=0.0)  # Deferred: computed in Phase 3 after validation gate
    dimensions: RarityDimensionScores
    combination_signature: str
    pillar_percentiles: dict[str, float]
    regime: RarityRegime = RarityRegime.EXPANSION
    is_generational: bool = False
    passed_gates: list[bool] = []  # [gate1, gate2, ..., gate6]
    universe_size: int = 0
    composite_raw_score: float = 0.0
    composite_tier: str = "none"
    sector: str | None = None
```

- [ ] **Step 2: Verify models import cleanly**

Run: `uv run python -c "from margin_engine.rarity.models import RarityResult, RarityConfig; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add engine/src/margin_engine/rarity/models.py
git commit -m "feat(rarity): add RarityResult and RarityConfig Pydantic models"
```

---

## Task 6: Quality Momentum Signal

**Files:**
- Create: `engine/src/margin_engine/rarity/quality_momentum.py`
- Test: `engine/tests/rarity/test_quality_momentum.py`

- [ ] **Step 1: Write quality momentum tests**

```python
# engine/tests/rarity/test_quality_momentum.py
"""Tests for temporal quality momentum scoring."""

from margin_engine.rarity.quality_momentum import compute_quality_momentum


def test_improving_trajectory():
    current = {"quality": 85.0, "value": 80.0, "momentum": 75.0, "growth": 82.0}
    history = [
        {"quality": 70.0, "value": 68.0, "momentum": 65.0, "growth": 70.0},  # Q-4
        {"quality": 73.0, "value": 71.0, "momentum": 68.0, "growth": 73.0},  # Q-3
        {"quality": 77.0, "value": 75.0, "momentum": 71.0, "growth": 77.0},  # Q-2
        {"quality": 81.0, "value": 78.0, "momentum": 73.0, "growth": 80.0},  # Q-1
    ]
    score = compute_quality_momentum(current, history)
    assert score > 70  # Strong improvement over 4 consecutive quarters


def test_stable_trajectory():
    current = {"quality": 80.0, "value": 75.0}
    history = [
        {"quality": 79.0, "value": 74.0},
        {"quality": 80.0, "value": 76.0},
        {"quality": 81.0, "value": 75.0},
        {"quality": 80.0, "value": 75.0},
    ]
    score = compute_quality_momentum(current, history)
    assert 40 <= score <= 60  # Roughly stable


def test_deteriorating_trajectory():
    current = {"quality": 60.0, "value": 55.0}
    history = [
        {"quality": 80.0, "value": 75.0},
        {"quality": 75.0, "value": 70.0},
        {"quality": 70.0, "value": 65.0},
        {"quality": 65.0, "value": 60.0},
    ]
    score = compute_quality_momentum(current, history)
    assert score < 40  # Clearly deteriorating


def test_insufficient_history_returns_neutral():
    current = {"quality": 85.0, "value": 80.0}
    history = [{"quality": 80.0, "value": 75.0}]  # Only 1 quarter
    score = compute_quality_momentum(current, history)
    assert score == 50.0


def test_empty_history_returns_neutral():
    current = {"quality": 85.0, "value": 80.0}
    score = compute_quality_momentum(current, [])
    assert score == 50.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_quality_momentum.py -v`
Expected: FAIL

- [ ] **Step 3: Implement quality momentum**

```python
# engine/src/margin_engine/rarity/quality_momentum.py
"""Temporal quality momentum — rate of change in fundamental quality.

Compares current pillar percentiles vs trailing quarters.
Returns 0-100 (>50 = improving, 50 = stable, <50 = deteriorating).
Requires 2+ prior quarters for a meaningful signal.
"""

from __future__ import annotations

import statistics


def compute_quality_momentum(
    current_pillars: dict[str, float],
    historical_pillars: list[dict[str, float]],
) -> float:
    """Compute quality momentum score (0-100).

    Algorithm:
    1. Compute average pillar percentile for current and each historical quarter
    2. Compute quarter-over-quarter deltas
    3. Count consecutive improving quarters
    4. Scale: 50 = stable, >70 requires 2+ consecutive improving quarters
    """
    if len(historical_pillars) < 2:
        return 50.0

    def _avg(pillars: dict[str, float]) -> float:
        vals = list(pillars.values())
        return statistics.mean(vals) if vals else 0.0

    current_avg = _avg(current_pillars)

    # Build time series: oldest first, then current
    series = [_avg(h) for h in historical_pillars] + [current_avg]

    # Quarter-over-quarter deltas
    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]

    if not deltas:
        return 50.0

    # Average delta (positive = improving)
    avg_delta = statistics.mean(deltas)

    # Count consecutive improving quarters (from most recent backward)
    consecutive_improving = 0
    for d in reversed(deltas):
        if d > 0:
            consecutive_improving += 1
        else:
            break

    # Score: base 50, +/- delta contribution, bonus for consecutive improvement
    # avg_delta of ~5 pctl points/quarter = strong signal
    delta_contribution = min(max(avg_delta * 4, -30), 30)  # Cap at ±30

    # Consecutive bonus: 2+ quarters = extra boost
    consecutive_bonus = min(consecutive_improving * 5, 20) if consecutive_improving >= 2 else 0

    score = 50.0 + delta_contribution + consecutive_bonus
    return round(min(max(score, 0.0), 100.0), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_quality_momentum.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/quality_momentum.py \
       engine/tests/rarity/test_quality_momentum.py
git commit -m "feat(rarity): add temporal quality momentum signal"
```

---

## Task 7: Smart Money Convergence Signal

**Files:**
- Create: `engine/src/margin_engine/rarity/smart_money.py`
- Test: `engine/tests/rarity/test_smart_money.py`

- [ ] **Step 1: Write smart money tests**

```python
# engine/tests/rarity/test_smart_money.py
"""Tests for smart money convergence scoring."""

from margin_engine.rarity.smart_money import compute_smart_money_convergence


def test_accumulation_only():
    score = compute_smart_money_convergence(
        accumulation_percentile=80.0,
        insider_cluster_percentile=20.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert score <= 60  # Max 60 with accumulation alone


def test_accumulation_plus_insider():
    score = compute_smart_money_convergence(
        accumulation_percentile=80.0,
        insider_cluster_percentile=75.0,
        accumulation_metadata=None,
        insider_metadata={"cluster_buy_detected": True},
    )
    assert 60 < score <= 80  # Max 80 with both


def test_full_convergence_with_metadata():
    score = compute_smart_money_convergence(
        accumulation_percentile=90.0,
        insider_cluster_percentile=85.0,
        accumulation_metadata={
            "n_quality_institutions_adding": 5,
            "n_consecutive_quarters_accumulated": 3,
        },
        insider_metadata={"cluster_buy_detected": True, "n_distinct_insiders": 4},
    )
    assert score > 80  # Strong convergence with all signals


def test_no_signals():
    score = compute_smart_money_convergence(
        accumulation_percentile=30.0,
        insider_cluster_percentile=25.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert score < 40  # Weak signal


def test_none_metadata_handled():
    # Should not raise
    score = compute_smart_money_convergence(
        accumulation_percentile=75.0,
        insider_cluster_percentile=70.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_smart_money.py -v`
Expected: FAIL

- [ ] **Step 3: Implement smart money convergence**

```python
# engine/src/margin_engine/rarity/smart_money.py
"""Smart money convergence scoring.

Combines institutional accumulation and insider cluster buying signals.
Uses FactorScore.metadata for intermediate signals when available,
falls back gracefully to percentile-only scoring.
"""

from __future__ import annotations


def compute_smart_money_convergence(
    accumulation_percentile: float,
    insider_cluster_percentile: float,
    accumulation_metadata: dict | None,
    insider_metadata: dict | None,
) -> float:
    """Compute smart money convergence score (0-100).

    Tiered scoring:
    - Institutional accumulation alone: max 60
    - + insider buying (cluster detected): max 80
    - + 3+ quality institutions adding: max 90
    - + 2+ consecutive quarters accumulated: max 100
    """
    # Base: weighted average of the two percentiles
    base = accumulation_percentile * 0.6 + insider_cluster_percentile * 0.4

    # Scale base to max 60 (accumulation-only ceiling)
    score = base * 0.6

    # Insider cluster bonus: up to +20
    insider_active = False
    if insider_metadata is not None:
        insider_active = insider_metadata.get("cluster_buy_detected", False)
    elif insider_cluster_percentile >= 70:
        insider_active = True

    if insider_active:
        score += 20 * (min(insider_cluster_percentile, 100) / 100)

    # Quality institutions bonus: up to +10
    if accumulation_metadata is not None:
        n_quality = accumulation_metadata.get("n_quality_institutions_adding", 0)
        if n_quality >= 3:
            score += 10.0
        elif n_quality >= 1:
            score += 5.0

    # Consecutive quarters bonus: up to +10
    if accumulation_metadata is not None:
        n_consecutive = accumulation_metadata.get("n_consecutive_quarters_accumulated", 0)
        if n_consecutive >= 2:
            score += 10.0

    return round(min(max(score, 0.0), 100.0), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_smart_money.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/smart_money.py \
       engine/tests/rarity/test_smart_money.py
git commit -m "feat(rarity): add smart money convergence signal"
```

---

## Task 8: Regime Classification + Alignment

**Files:**
- Create: `engine/src/margin_engine/rarity/regime.py`
- Test: `engine/tests/rarity/test_regime.py`

- [ ] **Step 1: Write regime tests**

```python
# engine/tests/rarity/test_regime.py
"""Tests for rarity regime classification and alignment scoring."""

from margin_engine.rarity.regime import classify_regime, compute_regime_alignment
from margin_engine.rarity.models import RarityRegime


def test_crisis_regime():
    regime = classify_regime(vix=40.0, yield_curve_slope=-0.5, credit_spread=3.0)
    assert regime == RarityRegime.CRISIS


def test_contraction_inverted_curve():
    regime = classify_regime(vix=18.0, yield_curve_slope=-0.3, credit_spread=1.5)
    assert regime == RarityRegime.CONTRACTION


def test_contraction_high_vix():
    regime = classify_regime(vix=28.0, yield_curve_slope=0.5, credit_spread=1.5)
    assert regime == RarityRegime.CONTRACTION


def test_late_cycle():
    regime = classify_regime(vix=20.0, yield_curve_slope=0.3, credit_spread=1.5)
    assert regime == RarityRegime.LATE_CYCLE


def test_expansion_default():
    regime = classify_regime(vix=14.0, yield_curve_slope=1.5, credit_spread=1.0)
    assert regime == RarityRegime.EXPANSION


def test_crisis_needs_both_conditions():
    # VIX > 35 but credit spread < 2.5 -> CONTRACTION (not CRISIS)
    regime = classify_regime(vix=38.0, yield_curve_slope=0.5, credit_spread=2.0)
    assert regime == RarityRegime.CONTRACTION


def test_alignment_value_in_contraction():
    # Value/mispricing favored in CONTRACTION
    score = compute_regime_alignment(
        regime=RarityRegime.CONTRACTION,
        winning_track="mispricing",
    )
    assert score > 70  # Favorable alignment


def test_alignment_growth_in_expansion():
    score = compute_regime_alignment(
        regime=RarityRegime.EXPANSION,
        winning_track="compounder",
    )
    assert score >= 50  # Neutral or favorable


def test_alignment_growth_in_crisis():
    # Growth not favored in crisis
    score = compute_regime_alignment(
        regime=RarityRegime.CRISIS,
        winning_track="compounder",
    )
    assert score < 50  # Unfavorable
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_regime.py -v`
Expected: FAIL

- [ ] **Step 3: Implement regime classification**

```python
# engine/src/margin_engine/rarity/regime.py
"""Rarity-specific regime classification and alignment scoring.

Standalone regime (independent of engine/src/margin_engine/regime/).
Purpose-built for rarity historical comparison with 4 simple classes.
"""

from __future__ import annotations

from margin_engine.rarity.models import RarityRegime

# Regime-to-favored-track mapping: {regime: {track: alignment_score}}
_REGIME_ALIGNMENT: dict[RarityRegime, dict[str, float]] = {
    RarityRegime.EXPANSION: {"compounder": 70.0, "mispricing": 40.0, "efficient_growth": 80.0},
    RarityRegime.LATE_CYCLE: {"compounder": 60.0, "mispricing": 55.0, "efficient_growth": 50.0},
    RarityRegime.CONTRACTION: {"compounder": 35.0, "mispricing": 80.0, "efficient_growth": 30.0},
    RarityRegime.CRISIS: {"compounder": 25.0, "mispricing": 90.0, "efficient_growth": 20.0},
}


def classify_regime(
    vix: float,
    yield_curve_slope: float,
    credit_spread: float,
) -> RarityRegime:
    """Classify current macro environment into one of 4 regimes.

    Evaluated in precedence order (first match wins):
    1. CRISIS: VIX > 35 AND credit spread > 2.5pp
    2. CONTRACTION: yield curve < 0 OR VIX > 25
    3. LATE_CYCLE: yield curve between -0.2 and 0.5 AND 15 <= VIX <= 25
    4. EXPANSION: default
    """
    if vix > 35 and credit_spread > 2.5:
        return RarityRegime.CRISIS

    if yield_curve_slope < 0 or vix > 25:
        return RarityRegime.CONTRACTION

    if -0.2 <= yield_curve_slope <= 0.5 and 15 <= vix <= 25:
        return RarityRegime.LATE_CYCLE

    return RarityRegime.EXPANSION


def compute_regime_alignment(
    regime: RarityRegime,
    winning_track: str,
) -> float:
    """Score 0-100: how well the current regime favors this stock's track.

    High score = regime historically rewards this type of opportunity.
    """
    alignment_map = _REGIME_ALIGNMENT.get(regime, {})
    return alignment_map.get(winning_track, 50.0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_regime.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/regime.py \
       engine/tests/rarity/test_regime.py
git commit -m "feat(rarity): add regime classification and alignment signal"
```

---

## Task 9: Historical Rarity Signal

**Files:**
- Create: `engine/src/margin_engine/rarity/historical_rarity.py`
- Test: `engine/tests/rarity/test_historical_rarity.py`

- [ ] **Step 1: Write historical rarity tests**

```python
# engine/tests/rarity/test_historical_rarity.py
"""Tests for historical frequency rarity scoring."""

from margin_engine.rarity.historical_rarity import compute_historical_frequency


def test_no_history_returns_neutral():
    score = compute_historical_frequency("Q90+V85+M80+G75", [])
    assert score == 50.0


def test_insufficient_quarters_returns_neutral():
    # Need >= 4 quarters
    snapshots = [
        {"signature": "Q90+V85+M80+G75", "quarter": "2025-Q1"},
        {"signature": "Q85+V80+M75+G70", "quarter": "2025-Q2"},
    ]
    score = compute_historical_frequency("Q90+V85+M80+G75", snapshots)
    assert score == 50.0


def test_never_seen_signature_is_rare():
    snapshots = [
        {"signature": "Q60+V55+M50+G45", "quarter": f"2024-Q{i}"} for i in range(1, 5)
    ] + [
        {"signature": "Q70+V65+M60+G55", "quarter": f"2025-Q{i}"} for i in range(1, 5)
    ]
    score = compute_historical_frequency("Q95+V90+M85+G88", snapshots)
    assert score > 80  # Very rare — never seen before


def test_common_signature_is_not_rare():
    sig = "Q70+V65+M60+G55"
    # Signature appears in every quarter
    snapshots = [{"signature": sig, "quarter": f"2024-Q{i}"} for i in range(1, 5)]
    snapshots += [{"signature": sig, "quarter": f"2025-Q{i}"} for i in range(1, 5)]
    score = compute_historical_frequency(sig, snapshots)
    assert score < 30  # Very common
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_historical_rarity.py -v`
Expected: FAIL

- [ ] **Step 3: Implement historical rarity**

```python
# engine/src/margin_engine/rarity/historical_rarity.py
"""Historical frequency rarity scoring.

Computes how often a given factor signature has appeared historically.
Returns 50 (neutral) until >= 4 quarters of data accumulate.
Uses exponential decay (half-life 20 quarters) to weight recent history.
"""

from __future__ import annotations

import math

_MIN_QUARTERS = 4
_HALF_LIFE = 20  # quarters


def compute_historical_frequency(
    current_signature: str,
    historical_snapshots: list[dict],
    lookback_quarters: int = 40,
) -> float:
    """Compute historical rarity score (0-100).

    Each snapshot is {"signature": str, "quarter": str}.
    Higher score = rarer (never seen = 100, always seen = 0).
    Returns 50.0 if fewer than _MIN_QUARTERS of history exist.
    """
    if len(historical_snapshots) < _MIN_QUARTERS:
        return 50.0

    # Limit to lookback window
    snapshots = historical_snapshots[-lookback_quarters:]
    total_snapshots = len(snapshots)

    # Count weighted matches using exponential decay
    # Most recent snapshot is index (total_snapshots - 1), oldest is index 0
    decay_rate = math.log(2) / _HALF_LIFE
    weighted_matches = 0.0
    total_weight = 0.0

    for i, snap in enumerate(snapshots):
        quarters_ago = total_snapshots - 1 - i
        weight = math.exp(-decay_rate * quarters_ago)
        total_weight += weight
        if snap["signature"] == current_signature:
            weighted_matches += weight

    if total_weight == 0:
        return 50.0

    frequency = weighted_matches / total_weight

    # Invert: high frequency = low rarity, low frequency = high rarity
    # Scale to 0-100
    rarity_score = (1.0 - frequency) * 100
    return round(min(max(rarity_score, 0.0), 100.0), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_historical_rarity.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/rarity/historical_rarity.py \
       engine/tests/rarity/test_historical_rarity.py
git commit -m "feat(rarity): add historical frequency rarity signal"
```

---

## Task 10: Rarity Orchestrator

**Files:**
- Create: `engine/src/margin_engine/rarity/rarity_engine.py`
- Test: `engine/tests/rarity/test_rarity_engine.py`

- [ ] **Step 1: Write orchestrator integration tests**

```python
# engine/tests/rarity/test_rarity_engine.py
"""Integration tests for the rarity engine orchestrator."""

import numpy as np

from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore
from margin_engine.rarity.models import RarityConfig, RarityRegime
from margin_engine.rarity.rarity_engine import compute_rarity_for_universe


def _fb(name: str, pctl: float, weight: float = 0.25) -> FactorBreakdown:
    return FactorBreakdown(
        factor_name=name,
        weight=weight,
        sub_scores=[FactorScore(name=f"{name}_main", raw_value=1.0, percentile_rank=pctl)],
    )


def _make_composite(
    ticker: str, q: float, v: float, m: float, g: float, raw: float = 75.0
) -> CompositeScore:
    return CompositeScore(
        ticker=ticker,
        composite_percentile=raw,
        composite_raw_score=raw,
        quality=_fb("quality", q),
        value=_fb("value", v),
        momentum=_fb("momentum", m),
        growth=_fb("growth", g),
        filters_passed=[],
        data_coverage=0.9,
        winning_track="compounder",
    )


def test_basic_universe_scoring():
    composites = [
        _make_composite("AAA", q=92, v=88, m=85, g=90, raw=80),
        _make_composite("BBB", q=70, v=65, m=60, g=55, raw=65),
        _make_composite("CCC", q=80, v=78, m=76, g=74, raw=72),
    ]
    config = RarityConfig()
    results = compute_rarity_for_universe(
        composites=composites,
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=config,
    )
    assert len(results) == 3
    # AAA should have highest rarity (best on all dimensions)
    scores = {r.ticker: r.rarity_score for r in results}
    assert scores["AAA"] > scores["BBB"]
    assert scores["AAA"] > scores["CCC"]


def test_gate_cascade_filters():
    composites = [
        _make_composite("TOP", q=92, v=88, m=85, g=90, raw=80),  # EXCEPTIONAL
        _make_composite("MED", q=70, v=65, m=60, g=55, raw=68),  # MEDIUM tier
        _make_composite("LOW", q=50, v=45, m=40, g=35, raw=50),  # NONE tier
    ]
    config = RarityConfig()
    results = compute_rarity_for_universe(
        composites=composites,
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=config,
    )
    # MED fails Gate 1 (not EXCEPTIONAL/HIGH), LOW fails Gate 1
    # Only TOP should have all gates attempted
    top_result = next(r for r in results if r.ticker == "TOP")
    assert top_result.passed_gates[0] is True  # Gate 1: EXCEPTIONAL

    med_result = next(r for r in results if r.ticker == "MED")
    assert med_result.passed_gates[0] is False  # Gate 1: MEDIUM not in (EXCEPTIONAL, HIGH)

    low_result = next(r for r in results if r.ticker == "LOW")
    assert low_result.passed_gates[0] is False  # Gate 1: NONE tier


def test_empty_universe():
    results = compute_rarity_for_universe(
        composites=[],
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=RarityConfig(),
    )
    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/rarity/test_rarity_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement orchestrator**

```python
# engine/src/margin_engine/rarity/rarity_engine.py
"""Rarity engine orchestrator.

Coordinates all rarity signals, computes composite scores,
applies the gate cascade, and produces RarityResult for each stock.
"""

from __future__ import annotations

import numpy as np

from margin_engine.models.scoring import CompositeScore
from margin_engine.rarity.combination_signature import build_signature
from margin_engine.rarity.convergence import compute_convergence
from margin_engine.rarity.historical_rarity import compute_historical_frequency
from margin_engine.rarity.joint_rarity import compute_all_joint_rarities
from margin_engine.rarity.models import (
    RarityConfig,
    RarityDimensionScores,
    RarityRegime,
    RarityResult,
)
from margin_engine.rarity.pillar_extraction import extract_pillar_percentiles
from margin_engine.rarity.quality_momentum import compute_quality_momentum
from margin_engine.rarity.regime import compute_regime_alignment
from margin_engine.rarity.smart_money import compute_smart_money_convergence


def _build_factor_matrix(
    all_pillars: list[dict[str, float]],
) -> np.ndarray:
    """Build an N×4 numpy matrix from pillar dicts.

    Columns: quality, value, momentum/catalyst (col 2), growth (col 3).
    Track B stocks get NaN in column 3 (growth missing).
    """
    col_order = ["quality", "value"]
    # Column 2: momentum or catalyst (whichever is present)
    # Column 3: growth (NaN if missing)
    rows = []
    for pillars in all_pillars:
        row = [
            pillars.get("quality", 0.0),
            pillars.get("value", 0.0),
            pillars.get("momentum", pillars.get("catalyst", 0.0)),
            pillars.get("growth", float("nan")),
        ]
        rows.append(row)
    return np.array(rows, dtype=np.float64)


def _extract_smart_money_signals(
    composite: CompositeScore,
) -> tuple[float, float, dict | None, dict | None]:
    """Extract accumulation and insider signals from CompositeScore."""
    accum_pctl = 50.0
    insider_pctl = 50.0
    accum_meta = None
    insider_meta = None

    # Search sub_scores for institutional_accumulation and insider_cluster
    for breakdown in [composite.quality, composite.value, composite.momentum]:
        for sub in breakdown.sub_scores:
            if "accumulation" in sub.name.lower() or "institutional" in sub.name.lower():
                accum_pctl = sub.percentile_rank
                accum_meta = sub.metadata
            elif "insider" in sub.name.lower() or "cluster" in sub.name.lower():
                insider_pctl = sub.percentile_rank
                insider_meta = sub.metadata

    # Also check optional breakdowns
    for breakdown in [composite.growth, composite.capital_allocation, composite.catalyst]:
        if breakdown is None:
            continue
        for sub in breakdown.sub_scores:
            if "accumulation" in sub.name.lower() or "institutional" in sub.name.lower():
                accum_pctl = sub.percentile_rank
                accum_meta = sub.metadata
            elif "insider" in sub.name.lower() or "cluster" in sub.name.lower():
                insider_pctl = sub.percentile_rank
                insider_meta = sub.metadata

    return accum_pctl, insider_pctl, accum_meta, insider_meta


def compute_rarity_for_universe(
    composites: list[CompositeScore],
    regime: RarityRegime,
    historical_snapshots: list[dict],
    config: RarityConfig | None = None,
    historical_pillars_by_ticker: dict[str, list[dict[str, float]]] | None = None,
) -> list[RarityResult]:
    """Compute rarity scores for all composites in the universe.

    Returns a RarityResult per composite (unfiltered — gate info in passed_gates).
    """
    if not composites:
        return []

    if config is None:
        config = RarityConfig()

    if historical_pillars_by_ticker is None:
        historical_pillars_by_ticker = {}

    # 1. Extract pillars for each stock
    all_pillars = [extract_pillar_percentiles(c) for c in composites]

    # 2. Build factor matrix and compute joint rarity
    matrix = _build_factor_matrix(all_pillars)
    joint_rarities = compute_all_joint_rarities(matrix)

    # 3. Compute per-stock signals
    results: list[RarityResult] = []
    for i, composite in enumerate(composites):
        pillars = all_pillars[i]
        pillar_values = list(pillars.values())

        # Signal 1: Joint rarity
        joint_rarity_pctl = joint_rarities[i]

        # Signal 2: Convergence
        convergence = compute_convergence(pillar_values)

        # Signal 3: Historical rarity
        signature = build_signature(pillars)
        hist_score = compute_historical_frequency(signature, historical_snapshots)

        # Signal 4: Quality momentum
        hist_pillars = historical_pillars_by_ticker.get(composite.ticker, [])
        qm_score = compute_quality_momentum(pillars, hist_pillars)

        # Signal 5: Smart money
        accum_pctl, insider_pctl, accum_meta, insider_meta = _extract_smart_money_signals(
            composite
        )
        sm_score = compute_smart_money_convergence(
            accum_pctl, insider_pctl, accum_meta, insider_meta
        )

        # Signal 6: Regime alignment
        winning_track = composite.winning_track or "compounder"
        regime_score = compute_regime_alignment(regime, winning_track)

        # Composite rarity score
        rarity_score = (
            config.joint_rarity_weight * joint_rarity_pctl
            + config.convergence_weight * convergence
            + config.historical_rarity_weight * hist_score
            + config.quality_momentum_weight * qm_score
            + config.smart_money_weight * sm_score
            + config.regime_alignment_weight * regime_score
        )
        rarity_score = round(min(max(rarity_score, 0.0), 100.0), 2)

        # Gate cascade
        tier = composite.composite_tier
        gate1 = tier in ("exceptional", "high")
        gate2 = all(p >= config.min_pillar_pctl for p in pillar_values) if gate1 else False
        gate3 = convergence >= config.convergence_gate if gate2 else False
        gate4 = rarity_score >= config.rarity_score_gate if gate3 else False
        # Gates 5 & 6 (hard cap + sector cap) applied at the caller level

        # Generational check
        n_pillars = len(pillar_values)
        pillars_above_80 = sum(1 for p in pillar_values if p >= 80)
        required_above_80 = 3 if n_pillars >= 4 else 2
        is_generational = (
            joint_rarity_pctl >= config.generational_joint_rarity_pctl
            and all(p >= config.min_pillar_pctl for p in pillar_values)
            and pillars_above_80 >= required_above_80
            and hist_score >= (1.0 - config.generational_hist_freq) * 100
            and composite.composite_raw_score >= config.generational_composite_raw
        )

        results.append(
            RarityResult(
                ticker=composite.ticker,
                rarity_score=rarity_score,
                dimensions=RarityDimensionScores(
                    joint_rarity_pctl=joint_rarity_pctl,
                    convergence_score=convergence,
                    historical_frequency=hist_score,
                    quality_momentum=qm_score,
                    smart_money_score=sm_score,
                    regime_alignment=regime_score,
                ),
                combination_signature=signature,
                pillar_percentiles=pillars,
                regime=regime,
                is_generational=is_generational,
                passed_gates=[gate1, gate2, gate3, gate4],
                universe_size=len(composites),
                composite_raw_score=composite.composite_raw_score,
                composite_tier=composite.composite_tier,
            ),
        )

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/rarity/test_rarity_engine.py -v`
Expected: 3 passed

- [ ] **Step 5: Run all rarity tests together**

Run: `uv run pytest engine/tests/rarity/ -v`
Expected: All tests pass (convergence, joint rarity, signature, pillar extraction, quality momentum, smart money, regime, historical, orchestrator)

- [ ] **Step 6: Commit**

```bash
git add engine/src/margin_engine/rarity/rarity_engine.py \
       engine/tests/rarity/test_rarity_engine.py
git commit -m "feat(rarity): add rarity engine orchestrator with gate cascade"
```

---

## Task 11: ORM Models + Alembic Migration

**Files:**
- Modify: `api/src/margin_api/db/models.py:1184`
- Create: Alembic migration

- [ ] **Step 1: Add ORM models to models.py**

Append after line 1183 in `api/src/margin_api/db/models.py`:

```python
# ---------------------------------------------------------------------------
# Rarity Engine tables
# ---------------------------------------------------------------------------


class RarityScore(Base):
    """Per-ticker rarity assessment from the rarity engine sidecar."""

    __tablename__ = "rarity_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    rarity_score: Mapped[float] = mapped_column(Float)
    joint_rarity_pctl: Mapped[float] = mapped_column(Float)
    convergence_score: Mapped[float] = mapped_column(Float)
    historical_frequency: Mapped[float] = mapped_column(Float)
    quality_momentum: Mapped[float] = mapped_column(Float)
    smart_money_score: Mapped[float] = mapped_column(Float)
    regime_alignment: Mapped[float] = mapped_column(Float)
    combination_signature: Mapped[str] = mapped_column(String(30))
    regime: Mapped[str] = mapped_column(String(20))
    conviction_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_generational: Mapped[bool] = mapped_column(default=False)
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    universe_size: Mapped[int] = mapped_column(default=0)

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        Index("ix_rarity_scores_asset_scored", "asset_id", "scored_at"),
    )


class RarityDistributionSnapshot(Base):
    """Per-run factor distribution summary for historical rarity baseline."""

    __tablename__ = "rarity_distribution_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scope: Mapped[str] = mapped_column(String(30))
    factor_name: Mapped[str] = mapped_column(String(50))
    n_obs: Mapped[int] = mapped_column()
    percentiles: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    mean: Mapped[float] = mapped_column(Float)
    std: Mapped[float] = mapped_column(Float)
```

- [ ] **Step 2: Create Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add rarity_scores and rarity_distribution_snapshots tables"`
Expected: New migration file created

- [ ] **Step 3: Verify migration and check for multiple heads**

Run: `uv run alembic heads`
Expected: Single head (no forks)

- [ ] **Step 4: Apply migration locally**

Run: `uv run alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/*.py
git commit -m "feat(rarity): add rarity_scores and rarity_distribution_snapshots ORM + migration"
```

---

## Task 12: Macro Data Client (Rename + Extend)

**Files:**
- Rename: `api/src/margin_api/data/fred_client.py` → `api/src/margin_api/data/macro_data_client.py`
- Modify: `api/src/margin_api/cli.py` (update import)
- Test: `api/tests/data/test_fred_client.py` → rename or update

- [ ] **Step 1: Rename file and update imports**

```bash
git mv api/src/margin_api/data/fred_client.py api/src/margin_api/data/macro_data_client.py
```

Then update the import in `api/src/margin_api/cli.py` — find `from margin_api.data.fred_client` and replace with `from margin_api.data.macro_data_client`.

Also rename the test file:
```bash
git mv api/tests/data/test_fred_client.py api/tests/data/test_macro_data_client.py
```

Update the test file's imports similarly.

- [ ] **Step 2: Add yield curve, credit spread, and VIX functions**

Append to `api/src/margin_api/data/macro_data_client.py`:

```python
async def fetch_yield_curve_slope() -> float:
    """Fetch 10Y-2Y Treasury yield curve slope from FRED.

    Returns spread in percentage points (e.g., 1.5 = 150bp).
    Falls back to 1.0 (normal slope) if unavailable.
    """
    cache_key = "yield_curve_slope"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED_API_KEY not set")

        async with httpx.AsyncClient(timeout=10.0) as client:
            dgs10_resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "DGS10",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            dgs10_resp.raise_for_status()
            dgs10 = float(dgs10_resp.json()["observations"][0]["value"])

            dgs2_resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "DGS2",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            dgs2_resp.raise_for_status()
            dgs2 = float(dgs2_resp.json()["observations"][0]["value"])

        value = dgs10 - dgs2
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable for yield curve, using default slope=1.0")
        return 1.0


async def fetch_credit_spread() -> float:
    """Fetch Baa-10Y Treasury credit spread from FRED (BAA10Y series).

    Returns spread in percentage points. Falls back to 2.0 if unavailable.
    """
    cache_key = "credit_spread"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED_API_KEY not set")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "BAA10Y",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            resp.raise_for_status()
            value = float(resp.json()["observations"][0]["value"])

        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable for credit spread, using default=2.0")
        return 2.0


async def fetch_vix() -> float:
    """Fetch current VIX level from yfinance.

    Falls back to 20.0 (normal) if unavailable.
    """
    cache_key = "vix"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        import yfinance as yf

        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="1d")
        if hist.empty:
            raise ValueError("No VIX data returned")
        value = float(hist["Close"].iloc[-1])
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("yfinance unavailable for VIX, using default=20.0")
        return 20.0
```

- [ ] **Step 3: Verify existing tests still pass with renamed file**

Run: `uv run pytest api/tests/data/test_macro_data_client.py -v`
Expected: Existing tests pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(api): rename fred_client to macro_data_client, add yield curve + credit spread + VIX"
```

---

## Task 13: compute_rarity Worker + Pipeline Sidecar

**Files:**
- Modify: `api/src/margin_api/workers.py:784-796` (enqueue sidecar)
- Modify: `api/src/margin_api/workers.py:3757-3787` (register function)
- Test: `api/tests/test_stage_scores.py` (verify sidecar enqueue)

- [ ] **Step 1: Add compute_rarity worker function**

Add after the `stage_scores` function in `api/src/margin_api/workers.py` (after line ~970). The function:

```python
# ---------------------------------------------------------------------------
# Rarity engine (parallel sidecar — runs alongside stage_scores)
# ---------------------------------------------------------------------------

RARITY_TIMEOUT = 300  # 5 minutes


async def compute_rarity(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
    scored_at_iso: str | None = None,
) -> dict:
    """Compute rarity scores for all v4-scored tickers.

    Runs as an independent sidecar — failure does not affect stage_scores.
    Reads V4Score detail JSONB, computes all 6 rarity dimensions,
    writes rarity_scores and rarity_distribution_snapshots tables.
    """
    import numpy as np

    from margin_engine.models.scoring import CompositeScore
    from margin_engine.rarity.combination_signature import build_signature
    from margin_engine.rarity.models import RarityConfig, RarityRegime
    from margin_engine.rarity.pillar_extraction import extract_pillar_percentiles
    from margin_engine.rarity.rarity_engine import compute_rarity_for_universe
    from margin_engine.rarity.regime import classify_regime

    from margin_api.data.macro_data_client import (
        fetch_credit_spread,
        fetch_vix,
        fetch_yield_curve_slope,
    )
    from margin_api.db.models import (
        Asset,
        RarityDistributionSnapshot,
        RarityScore,
        V4Score,
    )

    logger.info(
        "[rarity] Starting rarity computation (pipeline=%s, parent=%s)...",
        pipeline_id,
        parent_job_id,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Create JobRun
    async with session_factory() as session:
        job = JobRun(
            job_type="compute_rarity",
            status="running",
            triggered_by="chained",
            parent_job_id=parent_job_id,
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        scored_at = datetime.fromisoformat(scored_at_iso) if scored_at_iso else datetime.now(UTC)

        # 1. Load V4Scores
        async with session_factory() as session:
            result = await session.execute(
                select(V4Score, Asset.ticker, Asset.sector)
                .join(Asset, V4Score.asset_id == Asset.id)
                .where(V4Score.scored_at == scored_at)
            )
            rows = result.all()

        if not rows:
            logger.warning("[rarity] No V4Score rows for scored_at=%s", scored_at)
            async with session_factory() as session:
                r = await session.execute(select(JobRun).where(JobRun.id == job_id))
                j = r.scalar_one()
                j.status = "completed"
                j.progress = 1.0
                j.completed_at = datetime.now(UTC)
                await session.commit()
            return {"status": "completed", "scored": 0}

        # 2. Reconstruct CompositeScore from detail JSONB
        composites: list[CompositeScore] = []
        asset_ids: list[int] = []
        sectors: list[str | None] = []
        for v4_score, ticker, sector in rows:
            if v4_score.detail is None:
                continue
            try:
                cs = CompositeScore(**v4_score.detail)
                composites.append(cs)
                asset_ids.append(v4_score.asset_id)
                sectors.append(sector)
            except Exception as e:
                logger.debug("[rarity] Skip %s: %s", ticker, e)

        # 3. Fetch macro data for regime classification
        vix = await fetch_vix()
        yield_curve = await fetch_yield_curve_slope()
        credit_spread = await fetch_credit_spread()
        regime = classify_regime(vix, yield_curve, credit_spread)

        logger.info(
            "[rarity] Universe=%d, regime=%s (VIX=%.1f, YC=%.2f, CS=%.2f)",
            len(composites),
            regime.value,
            vix,
            yield_curve,
            credit_spread,
        )

        # 4. Run rarity engine
        config = RarityConfig()
        rarity_results = compute_rarity_for_universe(
            composites=composites,
            regime=regime,
            historical_snapshots=[],  # Accumulates over time
            config=config,
        )

        # 5. Write results
        async with session_factory() as session:
            for i, rr in enumerate(rarity_results):
                score = RarityScore(
                    asset_id=asset_ids[i],
                    scored_at=scored_at,
                    rarity_score=rr.rarity_score,
                    joint_rarity_pctl=rr.dimensions.joint_rarity_pctl,
                    convergence_score=rr.dimensions.convergence_score,
                    historical_frequency=rr.dimensions.historical_frequency,
                    quality_momentum=rr.dimensions.quality_momentum,
                    smart_money_score=rr.dimensions.smart_money_score,
                    regime_alignment=rr.dimensions.regime_alignment,
                    combination_signature=rr.combination_signature,
                    regime=rr.regime.value,
                    conviction_score=rr.conviction_score,
                    is_generational=rr.is_generational,
                    detail=rr.model_dump(mode="json"),
                    universe_size=rr.universe_size,
                )
                session.add(score)

            # Write distribution snapshots for future historical rarity
            all_pillars = [rr.pillar_percentiles for rr in rarity_results]
            factor_names = set()
            for p in all_pillars:
                factor_names.update(p.keys())
            for fname in sorted(factor_names):
                vals = [p[fname] for p in all_pillars if fname in p]
                if not vals:
                    continue
                arr = np.array(vals)
                snap = RarityDistributionSnapshot(
                    scored_at=scored_at,
                    scope="universe",
                    factor_name=fname,
                    n_obs=len(vals),
                    percentiles={
                        f"p{p}": round(float(np.percentile(arr, p)), 2)
                        for p in [5, 10, 25, 50, 75, 90, 95]
                    },
                    mean=round(float(arr.mean()), 2),
                    std=round(float(arr.std()), 2),
                )
                session.add(snap)

            await session.commit()

        # Mark job complete
        async with session_factory() as session:
            r = await session.execute(select(JobRun).where(JobRun.id == job_id))
            j = r.scalar_one()
            j.status = "completed"
            j.progress = 1.0
            j.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info("[rarity] Rarity computation complete: %d scored", len(rarity_results))
        return {"status": "completed", "scored": len(rarity_results), "regime": regime.value}

    except Exception as e:
        logger.exception("[rarity] Rarity computation failed: %s", e)
        try:
            async with session_factory() as session:
                r = await session.execute(select(JobRun).where(JobRun.id == job_id))
                j = r.scalar_one()
                j.status = "failed"
                j.error_message = str(e)[:500]
                j.completed_at = datetime.now(UTC)
                await session.commit()
        except Exception:
            pass
        return {"status": "failed", "error": str(e)[:200]}
```

- [ ] **Step 2: Add sidecar enqueue to full_score_v4**

In `api/src/margin_api/workers.py`, find the block at ~line 784-796 where `full_score_v4` enqueues `stage_scores`. Add the `compute_rarity` enqueue immediately after:

```python
        # Enqueue rarity computation as independent sidecar
        await redis.enqueue_job(
            "compute_rarity",
            pipeline_id,
            job_id,
            scored_at_iso,
            _job_id=f"compute_rarity:{uuid.uuid4().hex[:8]}",
        )
        logger.info("[score_v4] Chained -> compute_rarity (parallel sidecar, pipeline=%s)", pipeline_id)
```

- [ ] **Step 3: Register compute_rarity in WorkerSettings.functions**

In the `functions` list at ~line 3757, add:

```python
        arq_func(compute_rarity, timeout=300),
```

- [ ] **Step 4: Verify the worker module imports cleanly**

Run: `uv run python -c "from margin_api.workers import WorkerSettings; print(len(WorkerSettings.functions), 'functions')"`
Expected: prints the function count (should be 1 more than before)

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(rarity): add compute_rarity worker + parallel sidecar enqueue"
```

---

## Task 14: API Routes + Schemas

**Files:**
- Create: `api/src/margin_api/schemas/rarity.py`
- Create: `api/src/margin_api/routes/rarity.py`
- Modify: `api/src/margin_api/schemas/scores.py:170-173`
- Modify: `api/src/margin_api/app.py:37,165`
- Test: `api/tests/test_rarity_routes.py`

- [ ] **Step 1: Create rarity schemas**

```python
# api/src/margin_api/schemas/rarity.py
"""Response schemas for rarity API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class RarityDimensionsResponse(BaseModel):
    joint_rarity_pctl: float
    convergence_score: float
    historical_frequency: float
    quality_momentum: float
    smart_money_score: float
    regime_alignment: float


class RarityResponse(BaseModel):
    """Full rarity breakdown for a single ticker."""

    ticker: str
    rarity_score: float
    conviction_score: float
    is_generational: bool
    combination_signature: str
    regime: str
    dimensions: RarityDimensionsResponse
    pillar_percentiles: dict[str, float]
    universe_size: int
    scored_at: str | None = None


class RarityPickResponse(BaseModel):
    """Summary of a generational pick."""

    ticker: str
    name: str = ""
    sector: str | None = None
    rarity_score: float
    combination_signature: str
    is_generational: bool
    composite_tier: str = ""
    regime: str = ""


class RarityPicksListResponse(BaseModel):
    """List of top rarity picks."""

    picks: list[RarityPickResponse]
    regime: str
    universe_size: int
    scored_at: str | None = None
```

- [ ] **Step 2: Create rarity routes**

```python
# api/src/margin_api/routes/rarity.py
"""Rarity engine API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, RarityScore
from margin_api.db.session import get_db
from margin_api.schemas.rarity import (
    RarityDimensionsResponse,
    RarityPickResponse,
    RarityPicksListResponse,
    RarityResponse,
)

router = APIRouter(prefix="/api/v1/rarity", tags=["rarity"])


# IMPORTANT: /picks must be registered BEFORE /{ticker} to avoid
# FastAPI's greedy path parameter matching treating "picks" as a ticker.
@router.get("/picks", response_model=RarityPicksListResponse)
async def get_rarity_picks(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get top rarity picks (the generational opportunity list)."""
    # Get the most recent scored_at
    latest = await db.execute(
        select(RarityScore.scored_at)
        .order_by(RarityScore.scored_at.desc())
        .limit(1)
    )
    latest_row = latest.scalar_one_or_none()
    if not latest_row:
        return RarityPicksListResponse(picks=[], regime="unknown", universe_size=0)

    scored_at = latest_row

    result = await db.execute(
        select(RarityScore, Asset)
        .join(Asset, RarityScore.asset_id == Asset.id)
        .where(RarityScore.scored_at == scored_at)
        .order_by(RarityScore.rarity_score.desc())
        .limit(limit)
    )
    rows = result.all()

    picks = []
    regime = "unknown"
    universe_size = 0
    for rs, asset in rows:
        regime = rs.regime
        universe_size = rs.universe_size
        picks.append(
            RarityPickResponse(
                ticker=asset.ticker,
                name=asset.name or "",
                sector=asset.sector,
                rarity_score=rs.rarity_score,
                combination_signature=rs.combination_signature,
                is_generational=rs.is_generational,
                composite_tier=rs.detail.get("composite_tier", "") if rs.detail else "",
                regime=rs.regime,
            )
        )

    return RarityPicksListResponse(
        picks=picks,
        regime=regime,
        universe_size=universe_size,
        scored_at=scored_at.isoformat(),
    )


@router.get("/{ticker}", response_model=RarityResponse)
async def get_rarity(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get full rarity breakdown for a specific ticker."""
    result = await db.execute(
        select(RarityScore, Asset)
        .join(Asset, RarityScore.asset_id == Asset.id)
        .where(Asset.ticker == ticker.upper())
        .order_by(RarityScore.scored_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No rarity data for {ticker}")

    rs, asset = row
    detail = rs.detail or {}
    pillar_pctls = detail.get("pillar_percentiles", {})
    dims = detail.get("dimensions", {})

    return RarityResponse(
        ticker=asset.ticker,
        rarity_score=rs.rarity_score,
        conviction_score=rs.conviction_score,
        is_generational=rs.is_generational,
        combination_signature=rs.combination_signature,
        regime=rs.regime,
        dimensions=RarityDimensionsResponse(
            joint_rarity_pctl=dims.get("joint_rarity_pctl", rs.joint_rarity_pctl),
            convergence_score=dims.get("convergence_score", rs.convergence_score),
            historical_frequency=dims.get("historical_frequency", rs.historical_frequency),
            quality_momentum=dims.get("quality_momentum", rs.quality_momentum),
            smart_money_score=dims.get("smart_money_score", rs.smart_money_score),
            regime_alignment=dims.get("regime_alignment", rs.regime_alignment),
        ),
        pillar_percentiles=pillar_pctls,
        universe_size=rs.universe_size,
        scored_at=rs.scored_at.isoformat() if rs.scored_at else None,
    )
```

- [ ] **Step 3: Add rarity fields to ScoreResponse**

In `api/src/margin_api/schemas/scores.py`, add after line 173 (after `signal_history`):

```python
    # Rarity engine fields (populated when rarity sidecar has run)
    rarity_score: float | None = None
    is_generational: bool | None = None
    combination_signature: str | None = None
```

- [ ] **Step 4: Register rarity router in app.py**

In `api/src/margin_api/app.py`, add import:
```python
from margin_api.routes.rarity import router as rarity_router
```

Add registration:
```python
    app.include_router(rarity_router)
```

- [ ] **Step 5: Write route tests**

```python
# api/tests/test_rarity_routes.py
"""Tests for rarity API endpoints.

NOTE: This test requires the standard async SQLite fixture setup pattern used
throughout the API test suite. See api/tests/routes/test_transparency.py lines 24-63
for the full fixture boilerplate (async_engine, session_factory, db_session, app with
get_db dependency override). Copy that pattern here before running.
"""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.models import Asset, Base, RarityScore
from margin_api.db.session import get_db


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
def app(db_session):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    return application


@pytest.fixture
async def seed_rarity(db_session):
    """Seed an asset with a rarity score."""
    asset = Asset(ticker="AAPL", name="Apple Inc", sector="TECHNOLOGY")
    db_session.add(asset)
    await db_session.flush()

    scored_at = datetime(2026, 3, 16, tzinfo=UTC)
    rs = RarityScore(
        asset_id=asset.id,
        scored_at=scored_at,
        rarity_score=85.5,
        joint_rarity_pctl=90.0,
        convergence_score=72.0,
        historical_frequency=50.0,
        quality_momentum=65.0,
        smart_money_score=78.0,
        regime_alignment=70.0,
        combination_signature="Q90+V85+M80+G88",
        regime="expansion",
        conviction_score=72.0,
        is_generational=True,
        detail={
            "pillar_percentiles": {"quality": 90, "value": 85, "momentum": 80, "growth": 88},
            "dimensions": {
                "joint_rarity_pctl": 90.0,
                "convergence_score": 72.0,
                "historical_frequency": 50.0,
                "quality_momentum": 65.0,
                "smart_money_score": 78.0,
                "regime_alignment": 70.0,
            },
            "composite_tier": "exceptional",
        },
        universe_size=3000,
    )
    db_session.add(rs)
    await db_session.commit()
    return asset, rs


@pytest.mark.asyncio
async def test_get_rarity_ticker(app, seed_rarity):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/rarity/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["rarity_score"] == 85.5
    assert data["is_generational"] is True


@pytest.mark.asyncio
async def test_get_rarity_404(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/rarity/NONEXISTENT")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_rarity_picks(app, seed_rarity):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/rarity/picks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["picks"]) >= 1
    assert data["picks"][0]["ticker"] == "AAPL"
```

- [ ] **Step 6: Run route tests**

Run: `uv run pytest api/tests/test_rarity_routes.py -v`
Expected: 3 passed (may need adjustment based on existing test fixtures)

- [ ] **Step 7: Commit**

```bash
git add api/src/margin_api/schemas/rarity.py \
       api/src/margin_api/routes/rarity.py \
       api/src/margin_api/schemas/scores.py \
       api/src/margin_api/app.py \
       api/tests/test_rarity_routes.py
git commit -m "feat(rarity): add API routes, schemas, and ScoreResponse enrichment"
```

---

## Task 15: Extend Factor Functions with Metadata

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py`
- Modify: `engine/src/margin_engine/scoring/quantitative/insider_cluster.py`

- [ ] **Step 1: Read existing factor functions to understand return patterns**

Read `engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py` and `engine/src/margin_engine/scoring/quantitative/insider_cluster.py` to find where `FactorScore` is constructed and what intermediate values are available.

- [ ] **Step 2: Add metadata to institutional_accumulation FactorScore**

Where the function constructs `FactorScore(name=..., raw_value=..., percentile_rank=...)`, add a `metadata` parameter with the available intermediate signals:

```python
metadata={
    "n_quality_institutions_adding": n_quality_adding,  # variable name from existing code
    "n_consecutive_quarters_accumulated": consecutive_qtrs,
    "manager_tier_breakdown": tier_breakdown,
}
```

The exact variable names depend on what's in the existing function — adjust to match.

- [ ] **Step 3: Add metadata to insider_cluster FactorScore**

Similarly, add metadata to the insider cluster factor:

```python
metadata={
    "cluster_buy_detected": is_cluster,  # variable name from existing code
    "n_distinct_insiders": n_insiders,
    "total_buy_value": total_value,
}
```

- [ ] **Step 4: Run existing factor tests to verify no breakage**

Run: `uv run pytest engine/tests/ -k "accumulation or insider" -v`
Expected: All existing tests pass (metadata is optional, backward-compatible)

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/institutional_accumulation.py \
       engine/src/margin_engine/scoring/quantitative/insider_cluster.py
git commit -m "feat(rarity): populate FactorScore.metadata in accumulation and insider factors"
```

---

## Task 16: Full Integration Test

- [ ] **Step 1: Run all engine rarity tests**

Run: `uv run pytest engine/tests/rarity/ -v`
Expected: All pass

- [ ] **Step 2: Run all engine tests (regression check)**

Run: `uv run pytest engine/tests/ -v --ignore=engine/tests/backtesting/`
Expected: All pass (backtesting tests ignored for speed — they're slow)

- [ ] **Step 3: Run all API tests (regression check)**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All pass

- [ ] **Step 4: Lint check**

Run: `uv run ruff check engine/src/margin_engine/rarity/ api/src/margin_api/routes/rarity.py api/src/margin_api/schemas/rarity.py`
Expected: No errors

- [ ] **Step 5: Format check**

Run: `uv run ruff format --check engine/src/margin_engine/rarity/ api/src/margin_api/routes/rarity.py api/src/margin_api/schemas/rarity.py`
Expected: No changes needed

- [ ] **Step 6: Final commit if any lint fixes needed**

```bash
git add -A
git commit -m "fix: lint and format for rarity engine modules"
```
