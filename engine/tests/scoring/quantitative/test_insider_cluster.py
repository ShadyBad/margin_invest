"""Tests for the Insider Cluster Buying factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import InsiderTransaction
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.insider_cluster import insider_cluster_score


def _make_txn(
    date: str,
    name: str,
    title: str,
    txn_type: str,
    value: str,
    shares: int = 1000,
    is_first_purchase: bool | None = None,
) -> InsiderTransaction:
    """Helper to build an InsiderTransaction."""
    val = Decimal(value)
    price = val / shares if shares else Decimal("0")
    return InsiderTransaction(
        date=date,
        insider_name=name,
        title=title,
        transaction_type=txn_type,
        shares=shares,
        price_per_share=price,
        value=val,
        is_first_purchase=is_first_purchase,
    )


def _make_cluster(
    n: int = 3,
    buy_value: int = 200_000,
    title: str = "Director",
) -> list[InsiderTransaction]:
    """Helper to create n distinct insider buys within 90 days."""
    names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"]
    return [
        _make_txn(
            date=f"2025-06-{(i + 1):02d}",
            name=names[i],
            title=title,
            txn_type="buy",
            value=str(buy_value),
        )
        for i in range(n)
    ]


class TestInsiderClusterBuy:
    """Core cluster buying tests."""

    def test_three_distinct_insiders_cluster_buy(self):
        """3 distinct insiders buying > $100K within 90 days = cluster signal.

        Director (1pt) + Director (1pt) + Director (1pt) = 3.0 weighted score.
        """
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 3.0

    def test_four_insiders_higher_score(self):
        """4 distinct insiders should score higher than 3."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
            _make_txn("2025-07-10", "Dave", "Director", "buy", "180000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 4.0

    def test_same_insider_multiple_buys_counted_once(self):
        """Same insider buying multiple times counts as 1 distinct insider."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-10", "Alice", "Director", "buy", "200000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
        ]
        result = insider_cluster_score(transactions)
        # Only 2 distinct insiders: Alice (1pt) + Bob (1pt) = 2.0
        assert result.raw_value == 2.0


class TestCEOCFOWeighting:
    """CEO/CFO get 2x weight."""

    def test_ceo_gets_2x_weight(self):
        """CEO purchase should count as 2 points."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        # CEO (2pt) + Director (1pt) + Director (1pt) = 4.0
        assert result.raw_value == 4.0

    def test_cfo_gets_2x_weight(self):
        """CFO purchase should count as 2 points."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CFO", "buy", "300000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        # CFO (2pt) + Director (1pt) + Director (1pt) = 4.0
        assert result.raw_value == 4.0

    def test_ceo_and_cfo_both_buy(self):
        """CEO + CFO + Director = 2 + 2 + 1 = 5 points."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
            _make_txn("2025-06-10", "Bob", "CFO", "buy", "300000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 5.0

    def test_same_ceo_multiple_buys_counted_once_at_2x(self):
        """CEO buying multiple times still counts as one insider at 2x weight."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
            _make_txn("2025-06-20", "Alice", "CEO", "buy", "300000"),
            _make_txn("2025-07-01", "Bob", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        # CEO Alice (2pt) + Director Bob (1pt) = 3.0
        assert result.raw_value == 3.0


class TestSellsIgnored:
    """Selling transactions are ignored (asymmetric signal)."""

    def test_sells_are_filtered_out(self):
        """Sell transactions should be completely ignored."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-15", "Bob", "Director", "sell", "500000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        # Only 2 buys: Alice (1pt) + Carol (1pt) = 2.0 (Bob's sell is ignored)
        assert result.raw_value == 2.0

    def test_all_sells_no_buys(self):
        """If all transactions are sells, return raw_value=0.0."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "sell", "500000"),
            _make_txn("2025-06-15", "Bob", "CFO", "sell", "300000"),
            _make_txn("2025-07-01", "Carol", "Director", "sell", "200000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 0.0


class TestValueThreshold:
    """Purchases below $100K threshold are ignored."""

    def test_below_threshold_ignored(self):
        """Purchases under $100K are not significant and should be ignored."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "99999"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "50000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        # Only Carol's purchase is >= $100K: 1 director = 1.0
        assert result.raw_value == 1.0

    def test_exactly_100k_included(self):
        """Purchase of exactly $100K meets the threshold."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "100000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "100000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "100000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 3.0

    def test_all_below_threshold(self):
        """If all purchases are below $100K, return raw_value=0.0."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "50000"),
            _make_txn("2025-06-15", "Bob", "CFO", "buy", "75000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "25000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 0.0


class TestFewerThanThreeInsiders:
    """Fewer than 3 distinct insiders still returns a score, just lower."""

    def test_two_insiders(self):
        """2 insiders return a valid (but lower) weighted score."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 2.0

    def test_one_insider(self):
        """Single insider buy still returns a score."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
        ]
        result = insider_cluster_score(transactions)
        # CEO gets 2x weight
        assert result.raw_value == 2.0

    def test_one_director(self):
        """Single director buy returns 1.0."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 1.0


class TestEmptyAndEdgeCases:
    """Empty list and other edge cases."""

    def test_empty_list(self):
        """Empty list returns raw_value=0.0."""
        result = insider_cluster_score([])
        assert result.raw_value == 0.0

    def test_empty_list_detail(self):
        """Empty list has informative detail."""
        result = insider_cluster_score([])
        assert "no" in result.detail.lower() or "0" in result.detail

    def test_90_day_window_boundary(self):
        """Transactions outside the 90-day window from the most recent buy are excluded."""
        transactions = [
            # This is 91 days before the latest buy -- should be excluded
            _make_txn("2025-04-01", "Alice", "Director", "buy", "200000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        # Alice is 91 days before Carol (Jul 1), so only Bob + Carol = 2.0
        assert result.raw_value == 2.0

    def test_90_day_window_inclusive(self):
        """Transaction exactly 90 days before the most recent buy is included."""
        transactions = [
            # Exactly 90 days before Jul 1 is Apr 2
            _make_txn("2025-04-02", "Alice", "Director", "buy", "200000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        # Alice is exactly 90 days before Carol (Jul 1), so all 3 count = 3.0
        assert result.raw_value == 3.0


class TestFactorScoreFields:
    """Validate FactorScore metadata fields."""

    def test_name_is_insider_cluster(self):
        """Factor name should be 'insider_cluster'."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.name == "insider_cluster"

    def test_returns_factor_score_type(self):
        """Should return a FactorScore instance."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        assert isinstance(result, FactorScore)

    def test_percentile_rank_is_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6)."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.percentile_rank == 0.0

    def test_detail_contains_breakdown(self):
        """Detail string should show insider count and weighted score."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        # Should mention key computation components
        assert "3" in result.detail  # 3 distinct insiders
        assert "cluster" in result.detail.lower() or "insider" in result.detail.lower()

    def test_empty_list_name_and_percentile(self):
        """Empty list still has correct name and percentile."""
        result = insider_cluster_score([])
        assert result.name == "insider_cluster"
        assert result.percentile_rank == 0.0


class TestInsiderTransactionNewFields:
    """New fields on InsiderTransaction model."""

    def test_insider_cik_default_none(self):
        """insider_cik defaults to None for backward compat."""
        txn = _make_txn("2025-06-01", "Alice", "Director", "buy", "150000")
        assert txn.insider_cik is None

    def test_insider_cik_set(self):
        """insider_cik can be set."""
        txn = InsiderTransaction(
            date="2025-06-01",
            insider_name="Alice",
            title="Director",
            transaction_type="buy",
            shares=1000,
            price_per_share=Decimal("150"),
            value=Decimal("150000"),
            insider_cik="0001234567",
        )
        assert txn.insider_cik == "0001234567"

    def test_is_first_purchase_default_none(self):
        """is_first_purchase defaults to None for backward compat."""
        txn = _make_txn("2025-06-01", "Alice", "Director", "buy", "150000")
        assert txn.is_first_purchase is None

    def test_is_first_purchase_set(self):
        """is_first_purchase can be set explicitly."""
        txn = _make_txn(
            "2025-06-01",
            "Alice",
            "Director",
            "buy",
            "150000",
            is_first_purchase=True,
        )
        assert txn.is_first_purchase is True


class TestDrawdownBoost:
    """Price drawdown > 10% boosts insider cluster score by 1.5x."""

    def test_drawdown_boost(self):
        """Cluster during >10% drawdown gets 1.5x score."""
        txns = _make_cluster(3)
        base = insider_cluster_score(txns)
        boosted = insider_cluster_score(txns, price_drawdown_pct=-0.15)
        assert boosted.raw_value == pytest.approx(base.raw_value * 1.5)

    def test_no_drawdown_boost_above_threshold(self):
        """Drawdown <= 10% should not boost."""
        txns = _make_cluster(3)
        base = insider_cluster_score(txns)
        same = insider_cluster_score(txns, price_drawdown_pct=-0.05)
        assert same.raw_value == pytest.approx(base.raw_value)

    def test_no_drawdown_boost_at_exactly_minus_10(self):
        """Drawdown of exactly -10% should NOT boost (threshold is strictly < -0.10)."""
        txns = _make_cluster(3)
        base = insider_cluster_score(txns)
        same = insider_cluster_score(txns, price_drawdown_pct=-0.10)
        assert same.raw_value == pytest.approx(base.raw_value)

    def test_drawdown_none_no_boost(self):
        """None drawdown (default) should not boost."""
        txns = _make_cluster(3)
        base = insider_cluster_score(txns)
        same = insider_cluster_score(txns, price_drawdown_pct=None)
        assert same.raw_value == pytest.approx(base.raw_value)

    def test_drawdown_positive_no_boost(self):
        """Positive drawdown (price up) should not boost."""
        txns = _make_cluster(3)
        base = insider_cluster_score(txns)
        same = insider_cluster_score(txns, price_drawdown_pct=0.15)
        assert same.raw_value == pytest.approx(base.raw_value)


class TestMagnitudeBoost:
    """Opt-in magnitude multiplier based on total_buy_value."""

    def test_magnitude_5m_plus(self):
        """$5M+ total buys get 2.0x magnitude multiplier."""
        txns = _make_cluster(3, buy_value=2_000_000)  # 3 * 2M = $6M total
        no_mag = insider_cluster_score(txns)
        with_mag = insider_cluster_score(txns, apply_magnitude=True)
        assert with_mag.raw_value == pytest.approx(no_mag.raw_value * 2.0)

    def test_magnitude_1m_plus(self):
        """$1M+ total buys get 1.5x magnitude multiplier."""
        txns = _make_cluster(3, buy_value=400_000)  # 3 * 400K = $1.2M total
        no_mag = insider_cluster_score(txns)
        with_mag = insider_cluster_score(txns, apply_magnitude=True)
        assert with_mag.raw_value == pytest.approx(no_mag.raw_value * 1.5)

    def test_magnitude_100k_plus(self):
        """$100K+ total buys get 1.0x magnitude multiplier (no change)."""
        txns = _make_cluster(3, buy_value=100_000)  # 3 * 100K = $300K total
        no_mag = insider_cluster_score(txns)
        with_mag = insider_cluster_score(txns, apply_magnitude=True)
        assert with_mag.raw_value == pytest.approx(no_mag.raw_value * 1.0)

    def test_magnitude_below_100k(self):
        """Below $100K total buys get 0.5x magnitude multiplier."""
        # Single insider with exactly $100K buy (total = $100K), but we need < $100K total
        # Use a single $100K buy -- total is $100K so that's the 1.0x tier
        # To get below 100K total, we'd need < $100K individual buys, but those are
        # filtered out by the $100K significance threshold. So this tier only fires
        # if somehow total < $100K (unlikely with the significance filter).
        # Test it directly with the helper if exposed, but functionally
        # the 0.5x tier cannot trigger through normal flow since each buy must be >= $100K.
        # We test the helper separately below.
        pass

    def test_magnitude_default_off(self):
        """Magnitude is off by default -- no multiplier applied."""
        txns = _make_cluster(3, buy_value=5_000_000)
        result = insider_cluster_score(txns)
        no_mag = insider_cluster_score(txns, apply_magnitude=False)
        assert result.raw_value == pytest.approx(no_mag.raw_value)

    def test_magnitude_combined_with_drawdown(self):
        """Magnitude and drawdown boosts should stack multiplicatively."""
        txns = _make_cluster(3, buy_value=2_000_000)  # $6M total -> 2.0x
        base = insider_cluster_score(txns)
        combined = insider_cluster_score(txns, price_drawdown_pct=-0.20, apply_magnitude=True)
        # drawdown 1.5x * magnitude 2.0x = 3.0x
        assert combined.raw_value == pytest.approx(base.raw_value * 3.0)


class TestMagnitudeBoostHelper:
    """Direct tests for _magnitude_boost helper."""

    def test_5m_plus(self):
        from margin_engine.scoring.quantitative.insider_cluster import _magnitude_boost

        assert _magnitude_boost(5_000_000.0) == 2.0
        assert _magnitude_boost(10_000_000.0) == 2.0

    def test_1m_plus(self):
        from margin_engine.scoring.quantitative.insider_cluster import _magnitude_boost

        assert _magnitude_boost(1_000_000.0) == 1.5
        assert _magnitude_boost(4_999_999.0) == 1.5

    def test_100k_plus(self):
        from margin_engine.scoring.quantitative.insider_cluster import _magnitude_boost

        assert _magnitude_boost(100_000.0) == 1.0
        assert _magnitude_boost(999_999.0) == 1.0

    def test_below_100k(self):
        from margin_engine.scoring.quantitative.insider_cluster import _magnitude_boost

        assert _magnitude_boost(99_999.0) == 0.5
        assert _magnitude_boost(0.0) == 0.5


class TestFirstPurchaseWeight:
    """is_first_purchase=True gives 10x weight to that insider."""

    def test_first_buy_director_10x_weight(self):
        """Director with is_first_purchase=True gets 10x weight (10.0 instead of 1.0)."""
        txns = _make_cluster(3)
        txns[0] = _make_txn(
            "2025-06-01",
            "Alice",
            "Director",
            "buy",
            "200000",
            is_first_purchase=True,
        )
        result = insider_cluster_score(txns)
        # Alice: 10.0 (Director * 10x), Bob: 1.0, Carol: 1.0 = 12.0
        assert result.raw_value == pytest.approx(12.0)

    def test_first_buy_ceo_20x_weight(self):
        """CEO with is_first_purchase=True gets 20x weight (2.0 * 10 = 20.0)."""
        txns = [
            _make_txn(
                "2025-06-01",
                "Alice",
                "CEO",
                "buy",
                "500000",
                is_first_purchase=True,
            ),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(txns)
        # Alice: 20.0 (CEO 2x * 10x), Bob: 1.0, Carol: 1.0 = 22.0
        assert result.raw_value == pytest.approx(22.0)

    def test_first_buy_none_no_change(self):
        """is_first_purchase=None (default) does not change weight."""
        txns = _make_cluster(3)
        result = insider_cluster_score(txns)
        # All directors, no first purchase: 1.0 + 1.0 + 1.0 = 3.0
        assert result.raw_value == pytest.approx(3.0)

    def test_first_buy_false_no_change(self):
        """is_first_purchase=False does not change weight."""
        txns = _make_cluster(3)
        txns[0] = _make_txn(
            "2025-06-01",
            "Alice",
            "Director",
            "buy",
            "200000",
            is_first_purchase=False,
        )
        result = insider_cluster_score(txns)
        assert result.raw_value == pytest.approx(3.0)

    def test_multiple_first_buys(self):
        """Multiple insiders with first purchase all get 10x."""
        txns = [
            _make_txn(
                "2025-06-01",
                "Alice",
                "Director",
                "buy",
                "200000",
                is_first_purchase=True,
            ),
            _make_txn(
                "2025-06-15",
                "Bob",
                "Director",
                "buy",
                "200000",
                is_first_purchase=True,
            ),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(txns)
        # Alice: 10.0, Bob: 10.0, Carol: 1.0 = 21.0
        assert result.raw_value == pytest.approx(21.0)


class TestBackwardCompatibility:
    """All new parameters default to preserving existing behavior."""

    def test_old_call_signature_works(self):
        """Calling with just transactions (old API) works identically."""
        txns = _make_cluster(3)
        result = insider_cluster_score(txns)
        assert result.raw_value > 0
        assert result.name == "insider_cluster"

    def test_old_call_matches_explicit_defaults(self):
        """Old call signature == explicit defaults for new params."""
        txns = _make_cluster(3)
        old = insider_cluster_score(txns)
        explicit = insider_cluster_score(
            txns,
            price_drawdown_pct=None,
            apply_magnitude=False,
        )
        assert old.raw_value == pytest.approx(explicit.raw_value)

    def test_metadata_includes_total_buy_value(self):
        """Metadata still includes total_buy_value for magnitude reference."""
        txns = _make_cluster(3, buy_value=200_000)
        result = insider_cluster_score(txns)
        assert result.metadata is not None
        assert result.metadata["total_buy_value"] == pytest.approx(600_000.0)

    def test_existing_three_directors_unchanged(self):
        """Exact golden value: 3 directors = 3.0 (unchanged from old behavior)."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "Director", "buy", "150000"),
            _make_txn("2025-06-15", "Bob", "Director", "buy", "200000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 3.0

    def test_existing_ceo_cfo_director_unchanged(self):
        """Exact golden value: CEO+CFO+Director = 5.0 (unchanged)."""
        transactions = [
            _make_txn("2025-06-01", "Alice", "CEO", "buy", "500000"),
            _make_txn("2025-06-10", "Bob", "CFO", "buy", "300000"),
            _make_txn("2025-07-01", "Carol", "Director", "buy", "120000"),
        ]
        result = insider_cluster_score(transactions)
        assert result.raw_value == 5.0
