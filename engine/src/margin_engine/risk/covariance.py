"""Covariance estimation: Analytical Nonlinear Shrinkage (ANLS) and linear shrinkage.

Implements:
- Ledoit & Wolf (2020) Analytical Nonlinear Shrinkage
- Ledoit & Wolf (2004) Linear Shrinkage toward diagonal target
- Sample covariance
- QIS precision matrix via ANLS eigenvalue inversion
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import scipy.linalg
from pydantic import BaseModel


class CovarianceResult(BaseModel):
    """Result of a covariance estimation."""

    model_config = {"arbitrary_types_allowed": True}

    tickers: list[str]
    matrix: np.ndarray  # (n, n) covariance matrix
    method: Literal["anls", "linear", "sample"]
    sample_size: int
    condition_number: float
    shrinkage_intensity: float
    n_assets: int
    n_observations: int


def compute_sample_covariance(returns: np.ndarray) -> np.ndarray:
    """Compute raw sample covariance matrix s = x.T @ x / t (mean-centered).

    Args:
        returns: (t, n) matrix of returns.

    Returns:
        (n, n) sample covariance matrix.
    """
    t_obs = returns.shape[0]
    x_c = returns - returns.mean(axis=0, keepdims=True)
    return x_c.T @ x_c / t_obs


def _anls_shrink_eigenvalues(
    eigenvalues: np.ndarray,
    n_obs: int,
    n_assets: int,
) -> tuple[np.ndarray, float]:
    """Apply Analytical Nonlinear Shrinkage to eigenvalues.

    Implements the Ledoit & Wolf (2020) oracle formula using
    kernel-smoothed Hilbert transform of the sample spectral density.

    Args:
        eigenvalues: Sorted eigenvalues from sample covariance (ascending).
        n_obs: Number of observations T.
        n_assets: Number of assets N.

    Returns:
        Tuple of (shrunk eigenvalues, effective shrinkage intensity).
    """
    c = n_assets / n_obs  # concentration ratio

    # Eigenvalues (ascending from eigh)
    lam = eigenvalues.copy()

    # Bandwidth for kernel smoothing: Silverman-like rule
    h = n_obs ** (-1.0 / 3.0)

    # Build the companion Stieltjes transform via discretized Hilbert transform
    # of the sample spectral density (empirical spectral distribution)
    d_star = np.empty(n_assets, dtype=np.float64)

    for i in range(n_assets):
        d_i = lam[i]

        # Compute delta_i: imaginary part of Stieltjes transform at d_i
        # Using Gaussian kernel smoothing of the sample spectral density
        diffs = lam - d_i
        # Gaussian kernel scaled by eigenvalue magnitude
        scale = max(h * max(abs(d_i), 1e-10), 1e-10)
        kernel_vals = np.exp(-0.5 * (diffs / scale) ** 2) / (np.sqrt(2.0 * np.pi) * scale)

        # Spectral density at d_i (imaginary part of Stieltjes transform)
        delta_i = np.sum(kernel_vals) / (n_assets * np.pi)
        delta_i = max(delta_i, 1e-10)  # Floor to avoid division by zero

        # Regularization from imaginary part for Cauchy principal value
        eta_i = np.pi * c * d_i * delta_i

        # Kernel-regularized real part of Stieltjes transform
        reg = eta_i
        real_parts = diffs / (diffs**2 + reg**2)
        theta_i = np.sum(real_parts) / n_assets

        # Oracle shrinkage formula: Ledoit-Wolf 2020 Eq. (4.3)
        # d_i* = d_i / |1 - c - c*d_i*m_F(d_i)|^2
        real_part = 1.0 - c - c * d_i * theta_i
        imag_part = c * d_i * delta_i
        denom = real_part**2 + imag_part**2
        denom = max(denom, 1e-10)

        d_star[i] = d_i / denom

    # Ensure all shrunk eigenvalues are positive
    min_pos = np.min(d_star[d_star > 0]) if np.any(d_star > 0) else 1e-10
    d_star = np.maximum(d_star, min_pos)

    # Compute effective shrinkage intensity as relative change
    total_change = np.sum(np.abs(d_star - lam))
    total_original = np.sum(np.abs(lam))
    intensity = total_change / max(total_original, 1e-10)

    return d_star, float(min(intensity, 1.0))


def compute_anls_covariance(
    returns: np.ndarray,
    tickers: list[str] | None = None,
) -> CovarianceResult:
    """Compute covariance using Analytical Nonlinear Shrinkage (Ledoit & Wolf, 2020).

    Steps:
    1. Compute sample covariance
    2. Eigendecompose via scipy.linalg.eigh
    3. Apply ANLS oracle shrinkage to eigenvalues
    4. Reconstruct: Sigma* = Q @ diag(d*) @ Q.T, symmetrize

    Args:
        returns: (t, n) matrix of returns.
        tickers: Optional list of ticker names.

    Returns:
        CovarianceResult with method="anls".
    """
    t_obs, n = returns.shape
    if tickers is None:
        tickers = [f"asset_{i}" for i in range(n)]

    s_cov = compute_sample_covariance(returns)

    # Eigendecompose (eigh returns sorted ascending)
    eigenvalues, eigenvectors = scipy.linalg.eigh(s_cov)

    # Floor eigenvalues at small positive value before shrinkage
    eigenvalues = np.maximum(eigenvalues, 1e-14)

    # Apply ANLS shrinkage
    d_star, shrinkage_intensity = _anls_shrink_eigenvalues(eigenvalues, t_obs, n)

    # Reconstruct covariance
    sigma = eigenvectors @ np.diag(d_star) @ eigenvectors.T

    # Symmetrize (numerical cleanup)
    sigma = (sigma + sigma.T) / 2.0

    cond = float(np.max(d_star) / np.min(d_star))

    return CovarianceResult(
        tickers=tickers,
        matrix=sigma,
        method="anls",
        sample_size=t_obs,
        condition_number=cond,
        shrinkage_intensity=shrinkage_intensity,
        n_assets=n,
        n_observations=t_obs,
    )


def compute_linear_shrinkage(
    returns: np.ndarray,
    tickers: list[str] | None = None,
) -> CovarianceResult:
    """Compute covariance using Ledoit-Wolf (2004) linear shrinkage.

    Shrinks sample covariance toward diagonal target:
        Sigma* = alpha * diag(diag(S)) + (1 - alpha) * S

    Args:
        returns: (t, n) matrix of returns.
        tickers: Optional list of ticker names.

    Returns:
        CovarianceResult with method="linear".
    """
    t_obs, n = returns.shape
    if tickers is None:
        tickers = [f"asset_{i}" for i in range(n)]

    x_c = returns - returns.mean(axis=0, keepdims=True)
    s_cov = x_c.T @ x_c / t_obs

    # Target: diagonal of sample covariance
    target = np.diag(np.diag(s_cov))

    # Ledoit-Wolf 2004 optimal shrinkage intensity
    # alpha* = min(beta / delta, 1) where:
    #   delta = ||S - target||_F^2
    #   beta = (1/T^2) * sum_t ||x_t x_t' - S||_F^2

    diff = s_cov - target
    delta = np.sum(diff**2)

    # Compute beta: average squared Frobenius distance of outer products from S
    beta_sum = 0.0
    for t in range(t_obs):
        x_t = x_c[t : t + 1, :]  # (1, n)
        outer = x_t.T @ x_t  # (n, n)
        beta_sum += np.sum((outer - s_cov) ** 2)
    beta = beta_sum / (t_obs**2)

    if delta < 1e-14:
        alpha = 1.0
    else:
        alpha = min(beta / delta, 1.0)
    alpha = max(alpha, 0.0)

    sigma = alpha * target + (1.0 - alpha) * s_cov

    # Compute condition number
    eigvals = scipy.linalg.eigvalsh(sigma)
    eigvals = np.maximum(eigvals, 1e-14)
    cond = float(np.max(eigvals) / np.min(eigvals))

    return CovarianceResult(
        tickers=tickers,
        matrix=sigma,
        method="linear",
        sample_size=t_obs,
        condition_number=cond,
        shrinkage_intensity=float(alpha),
        n_assets=n,
        n_observations=t_obs,
    )


def _compute_anls_partial(
    returns: np.ndarray,
    tickers: list[str],
) -> CovarianceResult:
    """ANLS on non-zero eigenvalues with null-space fallback.

    When T < N but T >= N/2, the sample covariance has (N - T) zero
    eigenvalues. Apply ANLS shrinkage to the T non-zero eigenvalues
    and set the zero eigenvalues to the minimum shrunk eigenvalue.

    Args:
        returns: (t, n) matrix of returns where t < n.
        tickers: List of ticker names.

    Returns:
        CovarianceResult with method="anls".
    """
    t_obs, n = returns.shape
    s_cov = compute_sample_covariance(returns)

    eigenvalues, eigenvectors = scipy.linalg.eigh(s_cov)

    # Identify non-zero eigenvalues (those > small threshold)
    threshold = 1e-12
    nonzero_mask = eigenvalues > threshold
    n_nonzero = int(np.sum(nonzero_mask))

    if n_nonzero < 2:
        # Too few non-zero eigenvalues; fall back to linear
        return compute_linear_shrinkage(returns, tickers)

    # Apply ANLS only to non-zero eigenvalues
    nonzero_eigs = eigenvalues[nonzero_mask]
    d_star_nonzero, shrinkage_intensity = _anls_shrink_eigenvalues(nonzero_eigs, t_obs, n_nonzero)

    # Set null-space eigenvalues to minimum shrunk eigenvalue
    min_shrunk = float(np.min(d_star_nonzero))
    d_star = np.full(n, min_shrunk)
    d_star[nonzero_mask] = d_star_nonzero

    # Reconstruct
    sigma = eigenvectors @ np.diag(d_star) @ eigenvectors.T
    sigma = (sigma + sigma.T) / 2.0

    cond = float(np.max(d_star) / np.min(d_star))

    return CovarianceResult(
        tickers=tickers,
        matrix=sigma,
        method="anls",
        sample_size=t_obs,
        condition_number=cond,
        shrinkage_intensity=shrinkage_intensity,
        n_assets=n,
        n_observations=t_obs,
    )


def compute_covariance(
    returns: np.ndarray,
    tickers: list[str] | None = None,
    method: str = "auto",
    min_days: int = 60,
) -> CovarianceResult:
    """Dispatch covariance estimation by method.

    Auto selection logic (three-tier):
    - T >= N and T >= min_days: Full ANLS
    - T < N but T >= N/2: ANLS on non-zero eigenvalues, null-space fallback
    - T < N/4 or T < min_days: Linear shrinkage (Ledoit-Wolf 2004)

    "anls"/"linear"/"sample" forces that method regardless of T/N ratio.

    Args:
        returns: (t, n) matrix of returns.
        tickers: Optional list of ticker names.
        method: One of "auto", "anls", "linear", "sample".
        min_days: Minimum observations for ANLS in auto mode.

    Returns:
        CovarianceResult with the chosen method.
    """
    t_obs, n = returns.shape
    if tickers is None:
        tickers = [f"asset_{i}" for i in range(n)]

    if method == "auto":
        if t_obs >= n and t_obs >= min_days:
            chosen = "anls"
        elif t_obs >= n // 2 and t_obs >= min_days:
            chosen = "anls_partial"
        else:
            chosen = "linear"
    else:
        chosen = method

    if chosen == "anls":
        return compute_anls_covariance(returns, tickers)
    elif chosen == "anls_partial":
        return _compute_anls_partial(returns, tickers)
    elif chosen == "linear":
        return compute_linear_shrinkage(returns, tickers)
    elif chosen == "sample":
        s_cov = compute_sample_covariance(returns)
        eigvals = scipy.linalg.eigvalsh(s_cov)
        eigvals_pos = np.maximum(eigvals, 1e-14)
        cond = float(np.max(eigvals_pos) / np.min(eigvals_pos))
        return CovarianceResult(
            tickers=tickers,
            matrix=s_cov,
            method="sample",
            sample_size=t_obs,
            condition_number=cond,
            shrinkage_intensity=0.0,
            n_assets=n,
            n_observations=t_obs,
        )
    else:
        raise ValueError(f"Unknown covariance method: {method}")


def compute_qis_precision(returns: np.ndarray) -> np.ndarray:
    """Compute precision matrix via ANLS eigenvalue inversion.

    Q @ diag(1/d*) @ Q.T where d* are ANLS-shrunk eigenvalues.

    Args:
        returns: (t, n) matrix of returns.

    Returns:
        (n, n) precision matrix.
    """
    t_obs, n = returns.shape
    s_cov = compute_sample_covariance(returns)

    eigenvalues, eigenvectors = scipy.linalg.eigh(s_cov)
    eigenvalues = np.maximum(eigenvalues, 1e-14)

    d_star, _ = _anls_shrink_eigenvalues(eigenvalues, t_obs, n)

    # Invert shrunk eigenvalues for precision matrix
    precision = eigenvectors @ np.diag(1.0 / d_star) @ eigenvectors.T

    # Symmetrize
    precision = (precision + precision.T) / 2.0

    return precision
