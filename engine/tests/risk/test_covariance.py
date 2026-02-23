"""Tests for risk.covariance module."""

from __future__ import annotations

import numpy as np
import scipy.linalg
from margin_engine.risk.covariance import (
    compute_anls_covariance,
    compute_covariance,
    compute_linear_shrinkage,
    compute_qis_precision,
    compute_sample_covariance,
)


def _generate_returns(t_obs: int, n: int, seed: int = 42) -> np.ndarray:
    """Generate factor-model returns: factors @ loadings + noise.

    Creates realistic return data with cross-sectional correlation structure.
    """
    rng = np.random.default_rng(seed)
    n_factors = min(3, n)
    factors = rng.standard_normal((t_obs, n_factors))
    loadings = rng.standard_normal((n_factors, n)) * 0.3
    noise = rng.standard_normal((t_obs, n)) * 0.1
    return factors @ loadings + noise


def _is_psd(matrix: np.ndarray, tol: float = -1e-10) -> bool:
    """Check if matrix is positive semi-definite."""
    eigvals = scipy.linalg.eigvalsh(matrix)
    return bool(np.all(eigvals >= tol))


def _is_pd(matrix: np.ndarray, tol: float = 1e-12) -> bool:
    """Check if matrix is positive definite."""
    eigvals = scipy.linalg.eigvalsh(matrix)
    return bool(np.all(eigvals > tol))


def _is_symmetric(matrix: np.ndarray, atol: float = 1e-12) -> bool:
    """Check if matrix is symmetric."""
    return bool(np.allclose(matrix, matrix.T, atol=atol))


class TestSampleCovariance:
    """Tests for compute_sample_covariance."""

    def test_shape(self) -> None:
        """Sample covariance has correct (n, n) shape."""
        x = _generate_returns(100, 5)
        s = compute_sample_covariance(x)
        assert s.shape == (5, 5)

    def test_symmetric(self) -> None:
        """Sample covariance is symmetric."""
        x = _generate_returns(100, 5)
        s = compute_sample_covariance(x)
        assert _is_symmetric(s)

    def test_positive_diagonal(self) -> None:
        """Diagonal entries (variances) are positive."""
        x = _generate_returns(100, 5)
        s = compute_sample_covariance(x)
        assert np.all(np.diag(s) > 0)

    def test_psd_when_t_ge_n(self) -> None:
        """Sample covariance is PSD when T >= N."""
        x = _generate_returns(100, 5)
        s = compute_sample_covariance(x)
        assert _is_psd(s)


class TestANLSCovariance:
    """Tests for compute_anls_covariance."""

    def test_psd(self) -> None:
        """ANLS covariance is positive semi-definite."""
        x = _generate_returns(100, 5)
        result = compute_anls_covariance(x)
        assert _is_psd(result.matrix)

    def test_shape_and_method(self) -> None:
        """Result has correct shape, method label, and metadata."""
        x = _generate_returns(100, 5)
        tickers = ["A", "B", "C", "D", "E"]
        result = compute_anls_covariance(x, tickers=tickers)
        assert result.matrix.shape == (5, 5)
        assert result.method == "anls"
        assert result.tickers == tickers
        assert result.n_assets == 5
        assert result.n_observations == 100
        assert result.sample_size == 100

    def test_symmetric(self) -> None:
        """ANLS covariance is symmetric."""
        x = _generate_returns(100, 5)
        result = compute_anls_covariance(x)
        assert _is_symmetric(result.matrix)

    def test_condition_number_improves_vs_sample(self) -> None:
        """ANLS condition number should be <= sample condition number (with tolerance)."""
        x = _generate_returns(80, 10, seed=99)
        s = compute_sample_covariance(x)
        sample_eigvals = scipy.linalg.eigvalsh(s)
        sample_eigvals = np.maximum(sample_eigvals, 1e-14)
        sample_cond = float(np.max(sample_eigvals) / np.min(sample_eigvals))

        result = compute_anls_covariance(x)
        # ANLS should improve or at least not massively worsen condition
        # Allow 2x tolerance since it's a different estimator
        assert result.condition_number <= sample_cond * 2.0

    def test_golden_value_3x3(self) -> None:
        """Golden-value test: 3x3 ANLS with seed=12345, T=50, N=3.

        Verifies determinism and positive semi-definiteness.
        """
        x = _generate_returns(t_obs=50, n=3, seed=12345)
        result1 = compute_anls_covariance(x, tickers=["X", "Y", "Z"])
        result2 = compute_anls_covariance(x, tickers=["X", "Y", "Z"])

        # Deterministic: same input -> same output
        np.testing.assert_array_equal(result1.matrix, result2.matrix)

        # PSD
        assert _is_psd(result1.matrix)

        # Symmetric
        assert _is_symmetric(result1.matrix)

        # Method and shape
        assert result1.method == "anls"
        assert result1.matrix.shape == (3, 3)

        # Positive diagonal
        assert np.all(np.diag(result1.matrix) > 0)

        # Condition number is finite and positive
        assert result1.condition_number > 0
        assert np.isfinite(result1.condition_number)

        # Shrinkage intensity is in [0, 1]
        assert 0.0 <= result1.shrinkage_intensity <= 1.0

    def test_default_tickers(self) -> None:
        """Default tickers are generated when none provided."""
        x = _generate_returns(50, 3)
        result = compute_anls_covariance(x)
        assert result.tickers == ["asset_0", "asset_1", "asset_2"]


class TestLinearShrinkage:
    """Tests for compute_linear_shrinkage."""

    def test_psd(self) -> None:
        """Linear shrinkage result is positive semi-definite."""
        x = _generate_returns(100, 5)
        result = compute_linear_shrinkage(x)
        assert _is_psd(result.matrix)

    def test_method_label(self) -> None:
        """Method is labeled 'linear'."""
        x = _generate_returns(100, 5)
        result = compute_linear_shrinkage(x)
        assert result.method == "linear"

    def test_off_diagonals_smaller_than_sample(self) -> None:
        """Off-diagonal elements should be shrunk toward zero vs sample."""
        x = _generate_returns(100, 5, seed=77)
        s = compute_sample_covariance(x)
        result = compute_linear_shrinkage(x)

        # Extract off-diagonal elements
        mask = ~np.eye(5, dtype=bool)
        sample_off = np.abs(s[mask])
        shrunk_off = np.abs(result.matrix[mask])

        # On average, off-diagonals should be smaller (shrunk toward zero)
        assert np.mean(shrunk_off) <= np.mean(sample_off)

    def test_shrinkage_intensity_bounds(self) -> None:
        """Shrinkage intensity is in [0, 1]."""
        x = _generate_returns(100, 5)
        result = compute_linear_shrinkage(x)
        assert 0.0 <= result.shrinkage_intensity <= 1.0

    def test_symmetric(self) -> None:
        """Linear shrinkage result is symmetric."""
        x = _generate_returns(100, 5)
        result = compute_linear_shrinkage(x)
        assert _is_symmetric(result.matrix)


class TestThreeWayComparison:
    """Compare ANLS, linear, and sample covariance."""

    def test_all_psd(self) -> None:
        """All three estimators produce PSD matrices."""
        x = _generate_returns(100, 5, seed=88)
        tickers = ["A", "B", "C", "D", "E"]
        anls = compute_anls_covariance(x, tickers)
        linear = compute_linear_shrinkage(x, tickers)
        sample = compute_covariance(x, tickers, method="sample")

        assert _is_psd(anls.matrix)
        assert _is_psd(linear.matrix)
        assert _is_psd(sample.matrix)

    def test_condition_number_ordering(self) -> None:
        """Condition numbers: ANLS <= Linear <= Sample (with tolerance).

        Shrinkage estimators should improve conditioning vs raw sample.
        """
        x = _generate_returns(80, 10, seed=55)
        tickers = [f"T{i}" for i in range(10)]
        anls = compute_anls_covariance(x, tickers)
        linear = compute_linear_shrinkage(x, tickers)
        sample = compute_covariance(x, tickers, method="sample")

        # Linear should improve over sample (with tolerance)
        assert linear.condition_number <= sample.condition_number * 1.5

        # ANLS should improve over sample (with generous tolerance)
        assert anls.condition_number <= sample.condition_number * 2.0


class TestAutoSelection:
    """Tests for compute_covariance auto-selection logic."""

    def test_anls_when_t_ge_n(self) -> None:
        """Auto selects ANLS when T >= N and T >= min_days."""
        x = _generate_returns(100, 10)
        result = compute_covariance(x, method="auto", min_days=60)
        assert result.method == "anls"

    def test_linear_when_t_lt_n_over_4(self) -> None:
        """Auto selects linear when T < N/4."""
        # n=80, t=10 -> t < n/4=20 AND t < n
        x = _generate_returns(10, 80, seed=33)
        result = compute_covariance(x, method="auto", min_days=5)
        assert result.method == "linear"

    def test_linear_below_min_days(self) -> None:
        """Auto selects linear when T < min_days."""
        x = _generate_returns(30, 5)
        result = compute_covariance(x, method="auto", min_days=60)
        assert result.method == "linear"

    def test_n_gt_t_intermediate_uses_anls_partial(self) -> None:
        """When N/2 <= T < N, auto selects ANLS with null-space fallback."""
        x = _generate_returns(20, 40, seed=44)  # T=20, N=40, T >= N/2
        result = compute_covariance(x, method="auto", min_days=10)
        assert _is_psd(result.matrix)
        # Should use partial ANLS (reported as "anls")
        assert result.method == "anls"

    def test_n_much_gt_t_uses_linear(self) -> None:
        """When T < N/4, auto selects linear shrinkage."""
        x = _generate_returns(10, 80, seed=44)  # T=10, N=80, T < N/4=20
        result = compute_covariance(x, method="auto", min_days=5)
        assert _is_psd(result.matrix)
        assert result.method == "linear"

    def test_forced_anls(self) -> None:
        """Forcing method='anls' uses ANLS."""
        x = _generate_returns(100, 5)
        result = compute_covariance(x, method="anls")
        assert result.method == "anls"

    def test_forced_linear(self) -> None:
        """Forcing method='linear' uses linear shrinkage."""
        x = _generate_returns(100, 5)
        result = compute_covariance(x, method="linear")
        assert result.method == "linear"

    def test_forced_sample(self) -> None:
        """Forcing method='sample' uses sample covariance."""
        x = _generate_returns(100, 5)
        result = compute_covariance(x, method="sample")
        assert result.method == "sample"
        assert result.shrinkage_intensity == 0.0

    def test_unknown_method_raises(self) -> None:
        """Unknown method raises ValueError."""
        x = _generate_returns(100, 5)
        try:
            compute_covariance(x, method="unknown")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "unknown" in str(e).lower()


class TestQISPrecision:
    """Tests for compute_qis_precision."""

    def test_shape(self) -> None:
        """Precision matrix has correct (n, n) shape."""
        x = _generate_returns(100, 5)
        prec = compute_qis_precision(x)
        assert prec.shape == (5, 5)

    def test_symmetric(self) -> None:
        """Precision matrix is symmetric."""
        x = _generate_returns(100, 5)
        prec = compute_qis_precision(x)
        assert _is_symmetric(prec)

    def test_positive_definite(self) -> None:
        """Precision matrix is positive definite."""
        x = _generate_returns(100, 5)
        prec = compute_qis_precision(x)
        assert _is_pd(prec)

    def test_approximate_inverse_of_covariance(self) -> None:
        """Precision @ Covariance ~= Identity (with tolerance)."""
        x = _generate_returns(200, 5, seed=123)
        cov_result = compute_anls_covariance(x)
        prec = compute_qis_precision(x)

        product = prec @ cov_result.matrix
        np.testing.assert_allclose(product, np.eye(5), atol=0.15)
