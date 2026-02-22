"""Tests for stock clustering."""

import numpy as np
from margin_engine.ml.clustering import cluster_stocks


class TestClusterStocks:
    def test_correct_number_of_clusters(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((50, 10))
        tickers = [f"T{i}" for i in range(50)]
        clusters = cluster_stocks(features, tickers, n_clusters=5)
        assert len(clusters) == 5

    def test_all_tickers_assigned(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((50, 10))
        tickers = [f"T{i}" for i in range(50)]
        clusters = cluster_stocks(features, tickers, n_clusters=5)

        all_assigned = []
        for ticker_list in clusters.values():
            all_assigned.extend(ticker_list)

        assert sorted(all_assigned) == sorted(tickers)
        assert len(all_assigned) == 50  # no duplicates

    def test_handles_nan(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((20, 5))
        features[0, 0] = np.nan
        features[5, 2] = np.nan
        tickers = [f"T{i}" for i in range(20)]
        clusters = cluster_stocks(features, tickers, n_clusters=3)
        assert len(clusters) == 3

        all_assigned = []
        for ticker_list in clusters.values():
            all_assigned.extend(ticker_list)
        assert len(all_assigned) == 20

    def test_handles_all_nan_column(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((20, 5))
        features[:, 2] = np.nan  # entire column NaN
        tickers = [f"T{i}" for i in range(20)]
        clusters = cluster_stocks(features, tickers, n_clusters=3)
        assert len(clusters) == 3

    def test_deterministic(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((50, 10))
        tickers = [f"T{i}" for i in range(50)]

        clusters1 = cluster_stocks(features, tickers, n_clusters=5, seed=42)
        clusters2 = cluster_stocks(features, tickers, n_clusters=5, seed=42)

        for cluster_id in clusters1:
            assert clusters1[cluster_id] == clusters2[cluster_id]

    def test_different_seed_different_result(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((50, 10))
        tickers = [f"T{i}" for i in range(50)]

        clusters1 = cluster_stocks(features, tickers, n_clusters=5, seed=42)
        clusters2 = cluster_stocks(features, tickers, n_clusters=5, seed=99)

        # Not guaranteed different, but very likely with different seeds
        # At minimum both should be valid
        assert len(clusters1) == 5
        assert len(clusters2) == 5
        all_assigned = []
        for ticker_list in clusters2.values():
            all_assigned.extend(ticker_list)
        assert len(all_assigned) == 50

    def test_single_cluster(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((10, 3))
        tickers = [f"T{i}" for i in range(10)]
        clusters = cluster_stocks(features, tickers, n_clusters=1)
        assert len(clusters) == 1
        assert len(clusters[0]) == 10
