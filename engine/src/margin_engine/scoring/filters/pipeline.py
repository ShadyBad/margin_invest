"""Elimination filter pipeline — chains all 6 filters in sequence.

Runs every filter regardless of earlier failures (no short-circuit) to provide
complete diagnostic information about why an asset was eliminated.

Usage:
    result = run_elimination_filters(period, profile)
    if not result.passed:
        for f in result.failed_filters:
            print(f"{f.name}: {f.detail}")
"""

from __future__ import annotations

from dataclasses import dataclass

from margin_engine.models.financial import AssetProfile, FinancialPeriod
from margin_engine.models.scoring import FilterResult
from margin_engine.scoring.filters.altman import altman_z_score
from margin_engine.scoring.filters.beneish import beneish_m_score
from margin_engine.scoring.filters.current_ratio import current_ratio_check
from margin_engine.scoring.filters.fcf_distress import fcf_distress_check
from margin_engine.scoring.filters.interest_coverage import interest_coverage_check
from margin_engine.scoring.filters.liquidity import liquidity_check


@dataclass
class PipelineResult:
    """Result of running all elimination filters."""

    results: list[FilterResult]

    @property
    def passed(self) -> bool:
        """True if ALL filters passed."""
        return all(r.passed for r in self.results)

    @property
    def failed_filters(self) -> list[FilterResult]:
        """List of filters that failed."""
        return [r for r in self.results if not r.passed]


def run_elimination_filters(
    period: FinancialPeriod,
    profile: AssetProfile,
) -> PipelineResult:
    """Run all elimination filters in sequence.

    All filters run regardless of earlier failures (no short-circuit).
    This gives complete diagnostic information about why an asset was eliminated.

    Args:
        period: Financial data for scoring.
        profile: Static asset metadata (ticker, sector, market cap, etc.)

    Returns:
        PipelineResult containing all filter outcomes.
    """
    sector = profile.sector

    results = [
        liquidity_check(profile),
        beneish_m_score(period),
        altman_z_score(period, sector=sector),
        fcf_distress_check(period),
        interest_coverage_check(period, sector=sector),
        current_ratio_check(period, sector=sector),
    ]

    return PipelineResult(results=results)
