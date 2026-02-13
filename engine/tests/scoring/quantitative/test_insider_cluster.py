"""Tests for the Insider Cluster Buying factor."""

from decimal import Decimal

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
    )


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
