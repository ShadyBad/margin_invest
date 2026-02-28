"""Tests for Tier 3 detection — cross-sectional consistency checks."""

from margin_engine.healing.detection import _compute_mad, detect_tier3
from margin_engine.healing.models import (
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)


def _make_sector_dist(
    field_path: str,
    median: float,
    mad: float = 1.0,
    sector: str = "Technology",
    n_observations: int = 30,
    period: str = "2026-Q1",
) -> SectorDistribution:
    return SectorDistribution(
        sector=sector,
        field_path=field_path,
        median=median,
        mad=mad,
        n_observations=n_observations,
        period=period,
    )


class TestComputeMAD:
    """Tests for the _compute_mad helper."""

    def test_basic_mad(self) -> None:
        # values: [1, 2, 3, 4, 5], median=3, deviations=[2,1,0,1,2], mad=1.0
        assert _compute_mad([1.0, 2.0, 3.0, 4.0, 5.0]) == 1.0

    def test_identical_values_mad_zero(self) -> None:
        assert _compute_mad([5.0, 5.0, 5.0, 5.0]) == 0.0

    def test_two_values(self) -> None:
        # [10, 20], median=15, deviations=[5, 5], mad=5.0
        assert _compute_mad([10.0, 20.0]) == 5.0

    def test_single_value(self) -> None:
        assert _compute_mad([42.0]) == 0.0


class TestDetectTier3:
    """Tests for Tier 3 cross-sectional consistency detection."""

    def _default_config(self) -> HealingConfig:
        return HealingConfig()

    def test_deviation_from_history_sector_stable_flagged(self) -> None:
        """Deviation from own history AND sector stable -> flagged as SUSPICIOUS."""
        # Ticker's history is stable around 0.30 (gross_margin)
        # Current value is 0.90 — very far from history
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        # Sector median unchanged between periods
        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 1
        result = results[0]
        assert result.field_path == field
        assert result.severity == DetectionSeverity.SUSPICIOUS
        assert result.original_value == 0.90
        assert "self-history" in result.detail.lower() or "history" in result.detail.lower()

    def test_deviation_from_history_sector_also_moved_not_flagged(self) -> None:
        """Deviation from own history BUT sector also moved -> NOT flagged (regime shift)."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        # Sector median shifted significantly (from 0.30 to 0.85 — >10% of prior)
        current_dists = [_make_sector_dist(field, median=0.85, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.30, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_small_deviation_not_flagged(self) -> None:
        """Small deviation from history -> NOT flagged."""
        field = "income_statement.gross_margin"
        # Value 0.32 is close to the history median ~0.30, within 3.0 MAD
        field_values = {field: 0.32}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_fewer_than_4_history_points_skipped(self) -> None:
        """Fewer than 4 history points -> skipped entirely."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        # Only 3 history points
        ticker_history = {field: [0.30, 0.31, 0.29]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_no_prior_sector_distributions_skipped(self) -> None:
        """No prior sector distributions for the field -> skipped."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        # No prior distributions for this field
        prior_dists: list[SectorDistribution] = []

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_no_history_for_field_skipped(self) -> None:
        """Field not present in ticker_history -> skipped."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history: dict[str, list[float]] = {}  # No history at all

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_zero_mad_in_history_skipped(self) -> None:
        """If ticker's own MAD is 0, skip (constant history, deviation is meaningless)."""
        field = "income_statement.gross_margin"
        # All identical values -> MAD = 0
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.30, 0.30, 0.30]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_multiple_fields_processed(self) -> None:
        """Multiple fields are each evaluated independently."""
        field_a = "income_statement.gross_margin"
        field_b = "derived.revenue_growth"

        field_values = {field_a: 0.90, field_b: 5.0}
        ticker_history = {
            field_a: [0.30, 0.31, 0.29, 0.32, 0.30],
            field_b: [0.10, 0.12, 0.11, 0.09, 0.10],
        }

        # Both sectors stable
        current_dists = [
            _make_sector_dist(field_a, median=0.35, period="2026-Q1"),
            _make_sector_dist(field_b, median=0.12, period="2026-Q1"),
        ]
        prior_dists = [
            _make_sector_dist(field_a, median=0.34, period="2025-Q4"),
            _make_sector_dist(field_b, median=0.11, period="2025-Q4"),
        ]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        flagged_fields = {r.field_path for r in results}
        assert field_a in flagged_fields
        assert field_b in flagged_fields
        assert all(r.severity == DetectionSeverity.SUSPICIOUS for r in results)

    def test_sector_corroboration_disabled(self) -> None:
        """When sector corroboration is disabled, flag even if sector moved."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        # Sector moved dramatically
        current_dists = [_make_sector_dist(field, median=0.85, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.30, period="2025-Q4")]

        config = HealingConfig(tier3_sector_corroboration_required=False)
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        # Still flagged because we don't check sector corroboration
        assert len(results) == 1
        assert results[0].severity == DetectionSeverity.SUSPICIOUS

    def test_prior_sector_median_zero_skipped(self) -> None:
        """If prior sector median is 0, skip (can't compute relative movement)."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.0, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_no_current_sector_distribution_skipped(self) -> None:
        """No current sector distribution for the field -> skipped."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        # No current distribution for this field
        current_dists: list[SectorDistribution] = []
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 0

    def test_mad_deviation_populated(self) -> None:
        """The DetectionResult should include the computed MAD deviation."""
        field = "income_statement.gross_margin"
        field_values = {field: 0.90}
        ticker_history = {field: [0.30, 0.31, 0.29, 0.32, 0.30]}

        current_dists = [_make_sector_dist(field, median=0.35, period="2026-Q1")]
        prior_dists = [_make_sector_dist(field, median=0.34, period="2025-Q4")]

        config = self._default_config()
        results = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=current_dists,
            prior_sector_distributions=prior_dists,
            config=config,
        )

        assert len(results) == 1
        assert results[0].mad_deviation is not None
        assert results[0].mad_deviation > config.tier3_self_history_multiplier
