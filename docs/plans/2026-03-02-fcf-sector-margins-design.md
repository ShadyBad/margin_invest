# FCF Filter: Sector-Specific Margins + UI Clarity

**Date:** 2026-03-02
**Status:** Approved

## Problem

The FCF distress filter uses a single global `min_fcf_margin = -0.05` (-5%) floor. This is too permissive for capital-light sectors like Technology (where 15%+ FCF margins are normal) and provides no meaningful signal differentiation across sectors. The UI compounds this by displaying the threshold as `"Positive"` or `0.0`, hiding the actual multi-year rule from users.

## Design

### 1. Sector-Specific FCF Margin Thresholds

Add a hardcoded GICS sector → FCF margin floor mapping to `FcfDistressConfig`:

| GICS Sector              | FCF Margin Floor | Rationale                                        |
|--------------------------|------------------|--------------------------------------------------|
| Information Technology   | 10%              | Capital-light, high margins expected              |
| Communication Services   | 8%               | Media/telecom generate strong FCF                 |
| Health Care              | 5%               | Mix of pharma (high) and biotech (pre-revenue)    |
| Consumer Staples         | 5%               | Steady but thin-margin businesses                 |
| Consumer Discretionary   | 3%               | Cyclical + capital-intensive                      |
| Industrials              | 3%               | CapEx-heavy, cyclical                             |
| Materials                | 2%               | Commodity-driven, thin margins                    |
| Energy                   | 0%               | Highly cyclical, CapEx-heavy                      |
| Utilities                | 0%               | Regulated, low FCF margins by design              |
| Financials               | N/A              | Excluded from scoring universe                    |
| Real Estate              | N/A              | Excluded from scoring universe                    |

### 2. Engine Changes

**`FcfDistressConfig` (filter_config.py):**
- Add `sector_margin_overrides: dict[str, float]` with the sector map above as defaults
- Change `min_fcf_margin` from `-0.05` to `0.0` (fallback when sector is unknown)
- Add `get_min_fcf_margin(sector: str | None) -> float` helper method

**`fcf_distress_check_v2` (fcf_distress.py):**
- Look up sector-specific margin floor via `config.get_min_fcf_margin(sector)`
- Add `sector_fcf_margin_floor` and `sector_name` to `computed_metrics` dict
- Update detail string: `"median FCF margin 12.3% >= 10.0% floor (Information Technology)"`

**Unchanged:**
- v1 `fcf_distress_check` (legacy single-period)
- Cyclical relaxation (positive year count, separate dimension)
- Growth stock rescue paths (margin floor remains unconditional hard gate)

### 3. UI Changes

**`filter-card.tsx`:**

Replace the current display:
```
Value: $4.2B          Threshold: Positive
```

With expanded inline format reading from `computed_metrics`:
```
Value: 4/5 years positive · FCF margin 18.3%
Threshold: ≥ 3/5 years · margin ≥ 10% (Technology)
```

Failing example:
```
Value: 1/5 years positive · FCF margin -8.2%
Threshold: ≥ 2/5 years · margin ≥ 0% (Energy, cyclical)
```

Graceful fallback when `computed_metrics` is missing (v1 legacy responses): keep current display.

### 4. What Doesn't Change

- API endpoints and response schema (`computed_metrics` is already a passthrough dict)
- Other elimination filters
- Scoring pipeline order

## Testing

**Engine (`test_fcf_distress.py`):**
- Parametrized golden-value tests for each sector's margin floor
- Tech stock with 8% FCF margin fails (below 10%), Energy stock with 0.5% passes
- Fallback default (0.0%) when sector is `None`
- YAML config loading with sector overrides

**Web (`filter-card.test.tsx`):**
- New inline format renders for passing/failing cases
- Sector name appears in threshold display
- Graceful fallback when `computed_metrics` is missing

## Scope

~3 files modified in engine, 1 in web, plus tests. No API changes, no migration.
