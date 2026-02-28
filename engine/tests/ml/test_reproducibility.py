"""Tests for reproducibility environment capture and data hashing."""

from __future__ import annotations

import re

from margin_engine.ml.reproducibility import capture_environment, compute_data_hash


class TestCaptureEnvironment:
    def test_returns_dict(self) -> None:
        env = capture_environment()
        assert isinstance(env, dict)

    def test_contains_python_version_starting_with_3(self) -> None:
        env = capture_environment()
        assert "python_version" in env
        assert env["python_version"].startswith("3.")

    def test_contains_platform_non_empty(self) -> None:
        env = capture_environment()
        assert "platform" in env
        assert isinstance(env["platform"], str)
        assert len(env["platform"]) > 0

    def test_contains_libraries_with_expected_packages(self) -> None:
        env = capture_environment()
        assert "libraries" in env
        libs = env["libraries"]
        assert isinstance(libs, dict)
        # These packages are installed in the engine workspace
        for pkg in ("numpy", "scikit-learn", "lightgbm"):
            assert pkg in libs, f"Missing library: {pkg}"

    def test_libraries_include_all_tracked_packages(self) -> None:
        env = capture_environment()
        libs = env["libraries"]
        expected = {"numpy", "scikit-learn", "lightgbm", "torch", "pandas", "scipy"}
        assert expected.issubset(set(libs.keys()))

    def test_contains_determinism_flags(self) -> None:
        env = capture_environment()
        assert "determinism_flags" in env
        flags = env["determinism_flags"]
        assert isinstance(flags, dict)
        assert "PYTHONHASHSEED" in flags

    def test_contains_git_commit(self) -> None:
        env = capture_environment()
        assert "git_commit" in env
        assert isinstance(env["git_commit"], str)
        assert len(env["git_commit"]) > 0


class TestComputeDataHash:
    def test_same_input_same_hash(self) -> None:
        h1 = compute_data_hash(["AAPL", "MSFT"], "2026-01-01T00:00:00Z")
        h2 = compute_data_hash(["AAPL", "MSFT"], "2026-01-01T00:00:00Z")
        assert h1 == h2

    def test_different_input_different_hash(self) -> None:
        h1 = compute_data_hash(["AAPL", "MSFT"], "2026-01-01T00:00:00Z")
        h2 = compute_data_hash(["AAPL", "GOOG"], "2026-01-01T00:00:00Z")
        assert h1 != h2

    def test_different_timestamp_different_hash(self) -> None:
        h1 = compute_data_hash(["AAPL"], "2026-01-01T00:00:00Z")
        h2 = compute_data_hash(["AAPL"], "2026-02-01T00:00:00Z")
        assert h1 != h2

    def test_order_independent(self) -> None:
        h1 = compute_data_hash(["MSFT", "AAPL"], "2026-01-01T00:00:00Z")
        h2 = compute_data_hash(["AAPL", "MSFT"], "2026-01-01T00:00:00Z")
        assert h1 == h2

    def test_returns_64_char_hex_string(self) -> None:
        h = compute_data_hash(["AAPL"], "2026-01-01T00:00:00Z")
        assert len(h) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", h)

    def test_empty_tickers(self) -> None:
        h = compute_data_hash([], "2026-01-01T00:00:00Z")
        assert len(h) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", h)
