"""Tests for backtest seed parameter support."""

from __future__ import annotations

from margin_engine.backtesting.replay_orchestrator import ReplayConfig

from margin_api.schemas.backtest import ReplayConfigRequest
from margin_api.services.backtest import compute_config_hash


class TestReplayConfigRequestSeed:
    """Tests for seed field on the API schema."""

    def test_seed_defaults_to_none(self) -> None:
        config = ReplayConfigRequest()
        assert config.seed is None

    def test_seed_can_be_set(self) -> None:
        config = ReplayConfigRequest(seed=42)
        assert config.seed == 42

    def test_seed_included_in_serialization(self) -> None:
        config = ReplayConfigRequest(seed=99)
        dumped = config.model_dump()
        assert dumped["seed"] == 99

    def test_seed_none_excluded_from_json_when_exclude_none(self) -> None:
        config = ReplayConfigRequest(seed=None)
        json_str = config.model_dump_json(exclude_none=True)
        assert "seed" not in json_str


class TestReplayConfigSeed:
    """Tests for seed field on the engine ReplayConfig."""

    def test_seed_defaults_to_none(self) -> None:
        config = ReplayConfig()
        assert config.seed is None

    def test_seed_can_be_set(self) -> None:
        config = ReplayConfig(seed=42)
        assert config.seed == 42


class TestConfigHashWithSeed:
    """Tests that different seeds produce different config hashes."""

    def test_different_seeds_produce_different_hashes(self) -> None:
        config_a = ReplayConfig(seed=42)
        config_b = ReplayConfig(seed=99)
        assert compute_config_hash(config_a) != compute_config_hash(config_b)

    def test_same_seed_produces_same_hash(self) -> None:
        config_a = ReplayConfig(seed=42)
        config_b = ReplayConfig(seed=42)
        assert compute_config_hash(config_a) == compute_config_hash(config_b)

    def test_none_seed_excluded_from_hash(self) -> None:
        """seed=None is excluded via exclude_none=True, so hash matches no-seed config."""
        config_with_none = ReplayConfig(seed=None)
        config_without = ReplayConfig()
        assert compute_config_hash(config_with_none) == compute_config_hash(config_without)

    def test_seed_zero_differs_from_none(self) -> None:
        """seed=0 is a valid value and should differ from seed=None."""
        config_zero = ReplayConfig(seed=0)
        config_none = ReplayConfig(seed=None)
        assert compute_config_hash(config_zero) != compute_config_hash(config_none)
