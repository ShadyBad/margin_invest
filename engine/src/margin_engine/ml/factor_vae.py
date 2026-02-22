"""FactorVAE: Variational Autoencoder for factor-based alpha prediction.

Implements prior-posterior learning where:
- Encoder (posterior): sees features + future returns during training
- Predictor (prior): sees only features, used at inference
- Decoder: maps latent z to predicted returns

Loss = reconstruction_loss + KL(posterior || prior)
"""

from __future__ import annotations

import io

import numpy as np
import torch
import torch.nn as nn
from pydantic import BaseModel
from scipy.stats import spearmanr


class FactorVAEConfig(BaseModel):
    """Configuration for FactorVAE."""

    latent_dim: int = 8
    hidden_dim: int = 64
    learning_rate: float = 1e-3
    epochs: int = 100
    kl_weight: float = 1.0
    enable: bool = False  # Disabled by default until enablement gate passes


class FactorVAEMetrics(BaseModel):
    """Training metrics for FactorVAE."""

    rank_ic: float = 0.0
    reconstruction_loss: float = 0.0
    kl_divergence: float = 0.0
    mean_variance: float = 0.0


class _Encoder(nn.Module):
    """Posterior encoder: features + future_returns -> latent distribution."""

    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(input_dim + 1, hidden_dim)  # +1 for future return
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

    def forward(
        self, features: torch.Tensor, returns: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.cat([features, returns.unsqueeze(-1)], dim=-1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc_mu(x), self.fc_logvar(x)


class _Predictor(nn.Module):
    """Prior predictor: features only -> latent distribution (used at inference)."""

    def __init__(self, input_dim: int, hidden_dim: int, latent_dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

    def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.relu(self.fc1(features))
        x = torch.relu(self.fc2(x))
        return self.fc_mu(x), self.fc_logvar(x)


class _Decoder(nn.Module):
    """Decoder: latent z -> predicted return."""

    def __init__(self, latent_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(latent_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(z))
        return self.fc2(x).squeeze(-1)


class FactorVAE(nn.Module):
    """Full FactorVAE model with prior-posterior learning."""

    def __init__(self, input_dim: int, config: FactorVAEConfig) -> None:
        super().__init__()
        self.encoder = _Encoder(input_dim, config.hidden_dim, config.latent_dim)
        self.predictor = _Predictor(input_dim, config.hidden_dim, config.latent_dim)
        self.decoder = _Decoder(config.latent_dim, config.hidden_dim)
        self.config = config

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Sample from the latent distribution using the reparameterization trick."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, features: torch.Tensor, returns: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass through both encoder (posterior) and predictor (prior)."""
        # Posterior (encoder)
        post_mu, post_logvar = self.encoder(features, returns)
        z = self.reparameterize(post_mu, post_logvar)
        pred_returns = self.decoder(z)

        # Prior (predictor)
        prior_mu, prior_logvar = self.predictor(features)

        return {
            "pred_returns": pred_returns,
            "post_mu": post_mu,
            "post_logvar": post_logvar,
            "prior_mu": prior_mu,
            "prior_logvar": prior_logvar,
        }


def _kl_divergence(
    post_mu: torch.Tensor,
    post_logvar: torch.Tensor,
    prior_mu: torch.Tensor,
    prior_logvar: torch.Tensor,
) -> torch.Tensor:
    """KL(posterior || prior) for diagonal Gaussians."""
    kl = 0.5 * (
        prior_logvar
        - post_logvar
        + (torch.exp(post_logvar) + (post_mu - prior_mu) ** 2) / torch.exp(prior_logvar)
        - 1.0
    )
    return kl.sum(dim=-1).mean()


def train_factor_vae(
    features: np.ndarray,
    forward_returns: np.ndarray,
    config: FactorVAEConfig | None = None,
    seed: int = 42,
) -> tuple[bytes, FactorVAEMetrics]:
    """Train FactorVAE model.

    Args:
        features: (N, F) feature matrix.
        forward_returns: (N,) forward return targets.
        config: VAE configuration. Uses defaults if None.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (serialized_state_dict_bytes, training_metrics).
    """
    if config is None:
        config = FactorVAEConfig()

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    _ = rng  # Seed numpy via default_rng for reproducibility

    n_samples, input_dim = features.shape
    model = FactorVAE(input_dim, config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    feat_t = torch.tensor(features, dtype=torch.float32)
    ret_t = torch.tensor(forward_returns, dtype=torch.float32)

    model.train()
    total_recon_loss = 0.0
    total_kl = 0.0

    for _epoch in range(config.epochs):
        optimizer.zero_grad()
        out = model(feat_t, ret_t)

        recon_loss = nn.functional.mse_loss(out["pred_returns"], ret_t)
        kl = _kl_divergence(
            out["post_mu"],
            out["post_logvar"],
            out["prior_mu"],
            out["prior_logvar"],
        )
        loss = recon_loss + config.kl_weight * kl
        loss.backward()
        optimizer.step()

        total_recon_loss = recon_loss.item()
        total_kl = kl.item()

    # Compute metrics
    model.eval()
    with torch.no_grad():
        prior_mu, prior_logvar = model.predictor(feat_t)
        z = model.reparameterize(prior_mu, prior_logvar)
        pred = model.decoder(z).numpy()

        # Rank IC (Spearman correlation between predicted and actual)
        if len(pred) > 2:
            ic, _ = spearmanr(pred, forward_returns)
            ic = 0.0 if np.isnan(ic) else float(ic)
        else:
            ic = 0.0

        mean_var = float(torch.exp(prior_logvar).mean().item())

    # Serialize
    buf = io.BytesIO()
    torch.save(model.state_dict(), buf)
    model_bytes = buf.getvalue()

    metrics = FactorVAEMetrics(
        rank_ic=ic,
        reconstruction_loss=total_recon_loss,
        kl_divergence=total_kl,
        mean_variance=mean_var,
    )
    return model_bytes, metrics


def predict_factor_vae(
    model_bytes: bytes,
    features: np.ndarray,
    config: FactorVAEConfig | None = None,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Predict using the prior (predictor) only.

    Args:
        model_bytes: Serialized model state dict bytes.
        features: (N, F) feature matrix.
        config: VAE configuration (must match training config).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (mean_predictions, variance_per_asset).
    """
    if config is None:
        config = FactorVAEConfig()

    torch.manual_seed(seed)
    _n_samples, input_dim = features.shape

    model = FactorVAE(input_dim, config)
    buf = io.BytesIO(model_bytes)
    state_dict = torch.load(buf, weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    feat_t = torch.tensor(features, dtype=torch.float32)
    with torch.no_grad():
        prior_mu, prior_logvar = model.predictor(feat_t)
        z_mu = prior_mu  # Use mean (no sampling for determinism)
        pred = model.decoder(z_mu).numpy()
        variance = torch.exp(prior_logvar).mean(dim=-1).numpy()

    return pred, variance
