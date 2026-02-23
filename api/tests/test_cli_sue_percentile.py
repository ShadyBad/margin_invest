"""Tests for SUE percentile computation in V3 scoring pipeline."""

from __future__ import annotations

from margin_engine.ingestion.normalizer import normalize_earnings_list
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.normalizer import compute_percentile_ranks
from margin_engine.scoring.quantitative.sue import sue_score


def _compute_sue_raw(earnings_data: dict) -> float:
    """Replicate the SUE raw score extraction logic from run_scoring_v3."""
    earnings_entries = earnings_data.get("earnings", [])
    if earnings_entries:
        surprises = normalize_earnings_list(earnings_entries)
        factor = sue_score(surprises)
        return factor.raw_value
    return 0.0


def _rank_sue_scores(sue_raw_scores: dict[str, float]) -> dict[str, float]:
    """Replicate the cross-universe percentile ranking from run_scoring_v3."""
    tickers = list(sue_raw_scores.keys())
    factors = [
        FactorScore(name="sue", raw_value=sue_raw_scores[t], percentile_rank=0.0)
        for t in tickers
    ]
    ranked = compute_percentile_ranks(factors, invert=False)
    return {t: ranked[i].percentile_rank for i, t in enumerate(tickers)}


# Sample earnings data with varying surprise magnitudes
EARNINGS_POSITIVE = {
    "earnings": [
        {"quarter": "2025-Q1", "actual_eps": 1.50, "expected_eps": 1.20},
        {"quarter": "2025-Q2", "actual_eps": 1.60, "expected_eps": 1.30},
        {"quarter": "2025-Q3", "actual_eps": 1.80, "expected_eps": 1.40},
        {"quarter": "2025-Q4", "actual_eps": 2.00, "expected_eps": 1.50},
    ]
}

EARNINGS_NEGATIVE = {
    "earnings": [
        {"quarter": "2025-Q1", "actual_eps": 1.00, "expected_eps": 1.20},
        {"quarter": "2025-Q2", "actual_eps": 0.90, "expected_eps": 1.30},
        {"quarter": "2025-Q3", "actual_eps": 0.80, "expected_eps": 1.10},
        {"quarter": "2025-Q4", "actual_eps": 0.70, "expected_eps": 1.00},
    ]
}

EARNINGS_MILD = {
    "earnings": [
        {"quarter": "2025-Q1", "actual_eps": 1.21, "expected_eps": 1.20},
        {"quarter": "2025-Q2", "actual_eps": 1.31, "expected_eps": 1.30},
        {"quarter": "2025-Q3", "actual_eps": 1.41, "expected_eps": 1.40},
        {"quarter": "2025-Q4", "actual_eps": 1.51, "expected_eps": 1.50},
    ]
}


class TestSuePercentileComputation:
    def test_raw_scores_differ_across_tickers(self):
        """Different earnings patterns produce different raw SUE scores."""
        raw_pos = _compute_sue_raw(EARNINGS_POSITIVE)
        raw_neg = _compute_sue_raw(EARNINGS_NEGATIVE)
        raw_mild = _compute_sue_raw(EARNINGS_MILD)

        assert raw_pos > 0, "Strong beats should produce positive SUE"
        assert raw_neg < 0, "Consistent misses should produce negative SUE"
        assert raw_pos > raw_mild, "Stronger beats > milder beats"

    def test_percentiles_spread_across_universe(self):
        """Multiple tickers with different earnings get different percentiles (not all 50.0)."""
        sue_raw = {
            "AAPL": _compute_sue_raw(EARNINGS_POSITIVE),
            "MSFT": _compute_sue_raw(EARNINGS_MILD),
            "INTC": _compute_sue_raw(EARNINGS_NEGATIVE),
        }
        pctls = _rank_sue_scores(sue_raw)

        assert len(pctls) == 3
        # Not all the same
        values = list(pctls.values())
        assert len(set(values)) > 1, f"Percentiles should not all be equal: {pctls}"

        # All in valid range
        for t, p in pctls.items():
            assert 0.0 <= p <= 100.0, f"{t} percentile {p} out of range"

        # Positive SUE ticker should rank highest
        assert pctls["AAPL"] > pctls["INTC"], "Positive SUE should rank above negative"

    def test_no_earnings_gets_zero_raw(self):
        """Ticker with no earnings data gets raw_value=0.0."""
        raw = _compute_sue_raw({})
        assert raw == 0.0

        raw_empty = _compute_sue_raw({"earnings": []})
        assert raw_empty == 0.0

    def test_no_earnings_ranks_lowest(self):
        """Ticker with no earnings (raw=0) ranks below a positive SUE ticker."""
        sue_raw = {
            "AAPL": _compute_sue_raw(EARNINGS_POSITIVE),
            "NODATA": 0.0,
            "INTC": _compute_sue_raw(EARNINGS_NEGATIVE),
        }
        pctls = _rank_sue_scores(sue_raw)

        # NODATA (0.0) should rank between positive and negative
        # (since negative SUE is below 0)
        assert pctls["AAPL"] > pctls["NODATA"]

    def test_single_ticker_gets_default_50(self):
        """Single ticker in universe gets percentile 50.0 from compute_percentile_ranks."""
        sue_raw = {"ONLY": _compute_sue_raw(EARNINGS_POSITIVE)}
        pctls = _rank_sue_scores(sue_raw)

        assert pctls["ONLY"] == 50.0

    def test_insufficient_earnings_quarters(self):
        """Fewer than 2 quarters of earnings data yields raw=0.0."""
        one_quarter = {
            "earnings": [
                {"quarter": "2025-Q4", "actual_eps": 2.00, "expected_eps": 1.50},
            ]
        }
        raw = _compute_sue_raw(one_quarter)
        assert raw == 0.0, "sue_score requires at least 2 quarters"
