# Scoring Logic Fixes — Design Document

**Date:** 2026-02-21
**Branch:** `feat/scoring-logic-fixes`
**Scope:** 14 independent fixes to `engine/src/margin_engine/scoring/`

## Goal

Fix 14 identified issues in the scoring pipeline that systematically limit candidate quality and portfolio construction. Each fix is independent, uses TDD, and gets its own commit.

## Git Strategy

Single feature branch (`feat/scoring-logic-fixes`), one commit per fix (`fix(engine): <description>`), merge to main when all 14 are done.

## Fixes Overview

### High-Impact (Fixes 1-10)

| Fix | Summary | Files | Risk |
|-----|---------|-------|------|
| 1 | MEDIUM conviction gets starter positions (not 0%) | v3_position_sizing.py | Low |
| 2 | Tiered IV gate based on quality floor score | v3_cascade.py | Medium |
| 3 | Relax ensemble convergence for asset-light sectors | ensemble_valuation.py, v3_cascade.py | Medium |
| 4 | Increase Track C position sizing to match compounder | v3_position_sizing.py | Low |
| 5 | MAD replaces CV for compounding power stability | v3_intermediates.py | Medium |
| 6 | Weight moat signatures by durability | moat_durability.py | Medium |
| 7 | Corroborated catalyst strength (weighted blend) | v3_intermediates.py, v3_cascade.py, v3_thresholds.py | Medium |
| 8 | Margin expansion solver for reverse DCF | reverse_dcf.py, v3_cascade.py | Higher |
| 9 | Style classifier tie-breaking with valuation signal | style_classifier.py | Low |
| 10 | Variable momentum weight by style | v4_weights.py | Low |

### Minor (Fixes 11-14)

| Fix | Summary | Files | Risk |
|-----|---------|-------|------|
| 11 | Regime-aware asset floor liquidation multiples | asset_floor.py | Low |
| 12 | Operating leverage floor for cost discipline | operating_leverage.py | Low |
| 13 | Median effective tax rate for ROIC stability | v3_intermediates.py | Low |
| 14 | TAM headroom cap + implausibility rejection | v3_track_c_cascade.py, v3_track_c_thresholds.py | Low |

## Execution Order

Easiest/highest-impact first:

1. Fix 1 — MEDIUM sizing
2. Fix 4 — Track C sizing
3. Fix 7 — Catalyst corroboration (threshold recalibration across 3 files)
4. Fix 9 — Style classifier tie-breaking
5. Fix 10 — Variable momentum weight
6. Fix 2 — Tiered IV gate
7. Fix 6 — Weighted moat signatures
8. Fix 5 — MAD for compounding stability
9. Fix 3 — Ensemble convergence for asset-light
10. Fix 8 — Margin expansion solver (new solver, TrackAInputs expansion)
11. Fix 11 — Regime-aware asset floor
12. Fix 12 — Operating leverage floor
13. Fix 13 — Median tax rate
14. Fix 14 — TAM headroom cap

## Risk Areas

- **Fix 7:** Threshold recalibration touches 3 files (v3_intermediates.py, v3_cascade.py, v3_thresholds.py). New weighted blend formula produces lower values by design, so thresholds must be lowered in lockstep.
- **Fix 8:** New binary search solver + 4 optional fields added to TrackAInputs. Gate 4 logic branches on field availability. Most complex single fix.

## Validation

Spec validated against codebase on 2026-02-21: all file paths, function signatures, variable names, current code snippets, and test files confirmed accurate. Zero discrepancies.

## Detailed Spec

See `docs/plans/2026-02-20-scoring-logic-fixes-prompt.md` for exact code changes, test cases, and implementation details for each fix.
