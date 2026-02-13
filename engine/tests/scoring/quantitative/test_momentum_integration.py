"""Integration tests for momentum factor scoring."""

import datetime
from decimal import Decimal

from margin_engine.models.financial import (
    EarningsSurprise,
    InsiderTransaction,
    InstitutionalHolding,
    PriceBar,
)
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative import (
    insider_cluster_score,
    institutional_accumulation,
    price_momentum,
    sentiment_score,
    sue_score,
)


def _make_price_bars() -> list[PriceBar]:
    """Generate 13 months of synthetic daily price bars.

    Prices start at $100 and drift linearly up to $120 over ~395 calendar days.
    """
    start_date = datetime.date(2024, 1, 2)
    num_days = 280  # ~13 months of trading days
    start_price = 100.0
    end_price = 120.0
    bars: list[PriceBar] = []
    for i in range(num_days):
        d = start_date + datetime.timedelta(days=int(i * 395 / num_days))
        progress = i / (num_days - 1)
        price = start_price + (end_price - start_price) * progress
        p = Decimal(str(round(price, 2)))
        bars.append(
            PriceBar(
                date=d.isoformat(),
                open=p,
                high=p + Decimal("1.00"),
                low=p - Decimal("1.00"),
                close=p,
                volume=1_000_000,
            )
        )
    return bars


def _make_earnings_surprises() -> list[EarningsSurprise]:
    """Generate 4 quarters of positive earnings surprises."""
    return [
        EarningsSurprise(
            quarter="2024-Q1",
            actual_eps=Decimal("1.55"),
            expected_eps=Decimal("1.40"),
        ),
        EarningsSurprise(
            quarter="2024-Q2",
            actual_eps=Decimal("1.68"),
            expected_eps=Decimal("1.50"),
        ),
        EarningsSurprise(
            quarter="2024-Q3",
            actual_eps=Decimal("1.72"),
            expected_eps=Decimal("1.60"),
        ),
        EarningsSurprise(
            quarter="2024-Q4",
            actual_eps=Decimal("1.85"),
            expected_eps=Decimal("1.70"),
        ),
    ]


def _make_insider_transactions() -> list[InsiderTransaction]:
    """Generate 3 insiders buying within 90 days, each > $100K."""
    return [
        InsiderTransaction(
            date="2024-11-15",
            insider_name="Alice Smith",
            title="CEO",
            transaction_type="buy",
            shares=5000,
            price_per_share=Decimal("25.00"),
            value=Decimal("125000"),
        ),
        InsiderTransaction(
            date="2024-12-01",
            insider_name="Bob Jones",
            title="CFO",
            transaction_type="buy",
            shares=4500,
            price_per_share=Decimal("26.00"),
            value=Decimal("117000"),
        ),
        InsiderTransaction(
            date="2024-12-20",
            insider_name="Carol White",
            title="Director",
            transaction_type="buy",
            shares=4000,
            price_per_share=Decimal("27.00"),
            value=Decimal("108000"),
        ),
    ]


def _make_institutional_holdings() -> list[InstitutionalHolding]:
    """Generate 3 funds accumulating in the same quarter."""
    return [
        InstitutionalHolding(
            fund_name="Alpha Capital",
            quarter="2024-Q4",
            shares_held=500_000,
            shares_changed=500_000,
            is_new_position=True,
        ),
        InstitutionalHolding(
            fund_name="Beta Partners",
            quarter="2024-Q4",
            shares_held=300_000,
            shares_changed=50_000,
            is_new_position=False,
        ),
        InstitutionalHolding(
            fund_name="Gamma Fund",
            quarter="2024-Q4",
            shares_held=200_000,
            shares_changed=200_000,
            is_new_position=True,
        ),
    ]


_SENTIMENT_SCORE_INPUT = 2.5


class TestMomentumFactorIntegration:
    def test_all_momentum_factors_compute(self):
        """All 5 momentum sub-factors compute without error and return correct names."""
        pm = price_momentum(_make_price_bars())
        sue = sue_score(_make_earnings_surprises())
        ic = insider_cluster_score(_make_insider_transactions())
        ia = institutional_accumulation(_make_institutional_holdings())
        sent = sentiment_score(_SENTIMENT_SCORE_INPUT)

        assert pm.name == "price_momentum"
        assert sue.name == "sue"
        assert ic.name == "insider_cluster"
        assert ia.name == "institutional_accumulation"
        assert sent.name == "sentiment"

    def test_all_percentiles_are_placeholders(self):
        """All percentile_ranks should be 0.0 (filled in Phase 6)."""
        pm = price_momentum(_make_price_bars())
        sue = sue_score(_make_earnings_surprises())
        ic = insider_cluster_score(_make_insider_transactions())
        ia = institutional_accumulation(_make_institutional_holdings())
        sent = sentiment_score(_SENTIMENT_SCORE_INPUT)

        for score in [pm, sue, ic, ia, sent]:
            assert score.percentile_rank == 0.0, (
                f"{score.name} percentile should be 0.0"
            )

    def test_all_have_detail(self):
        """All momentum factors should include non-empty detail strings."""
        pm = price_momentum(_make_price_bars())
        sue = sue_score(_make_earnings_surprises())
        ic = insider_cluster_score(_make_insider_transactions())
        ia = institutional_accumulation(_make_institutional_holdings())
        sent = sentiment_score(_SENTIMENT_SCORE_INPUT)

        for score in [pm, sue, ic, ia, sent]:
            assert len(score.detail) > 0, f"{score.name} should have detail"

    def test_imports_from_package(self):
        """All 5 momentum functions importable from margin_engine.scoring.quantitative."""
        from margin_engine.scoring.quantitative import insider_cluster_score as ics
        from margin_engine.scoring.quantitative import institutional_accumulation as ia
        from margin_engine.scoring.quantitative import price_momentum as pm
        from margin_engine.scoring.quantitative import sentiment_score as ss
        from margin_engine.scoring.quantitative import sue_score as sue

        assert callable(pm)
        assert callable(sue)
        assert callable(ics)
        assert callable(ia)
        assert callable(ss)

    def test_momentum_factors_return_factor_scores(self):
        """All 5 momentum factors return FactorScore instances."""
        pm = price_momentum(_make_price_bars())
        sue = sue_score(_make_earnings_surprises())
        ic = insider_cluster_score(_make_insider_transactions())
        ia = institutional_accumulation(_make_institutional_holdings())
        sent = sentiment_score(_SENTIMENT_SCORE_INPUT)

        for result in [pm, sue, ic, ia, sent]:
            assert isinstance(result, FactorScore), (
                f"{result.name} should be a FactorScore, got {type(result)}"
            )
