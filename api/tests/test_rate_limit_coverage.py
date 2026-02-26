"""Tests for middleware/rate_limit.py — configure_limiter paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestConfigureLimiter:
    def test_disabled_when_not_enabled(self):
        """When enabled=False, limiter stays disabled."""
        from margin_api.middleware.rate_limit import configure_limiter, limiter

        configure_limiter(redis_url="redis://localhost:6379", enabled=False)
        assert limiter.enabled is False

    def test_disabled_when_empty_redis_url(self):
        """When redis_url is empty, limiter stays disabled."""
        from margin_api.middleware.rate_limit import configure_limiter, limiter

        configure_limiter(redis_url="", enabled=True)
        assert limiter.enabled is False

    def test_disabled_when_redis_unreachable(self):
        """When Redis is unreachable (check() returns False), limiter stays disabled."""
        mock_storage = MagicMock()
        mock_storage.check.return_value = False

        with patch(
            "limits.storage.storage_from_string",
            return_value=mock_storage,
        ):
            from margin_api.middleware.rate_limit import configure_limiter, limiter

            configure_limiter(redis_url="redis://localhost:6379", enabled=True)
            assert limiter.enabled is False

    def test_enabled_when_redis_reachable(self):
        """When Redis is reachable, limiter is enabled with storage."""
        mock_storage = MagicMock()
        mock_storage.check.return_value = True

        with patch(
            "limits.storage.storage_from_string",
            return_value=mock_storage,
        ):
            from margin_api.middleware.rate_limit import configure_limiter, limiter

            configure_limiter(redis_url="redis://localhost:6379", enabled=True)
            assert limiter.enabled is True

    def test_disabled_on_import_error(self):
        """When limits library throws an exception, limiter degrades to disabled."""
        with patch(
            "limits.storage.storage_from_string",
            side_effect=RuntimeError("import failed"),
        ):
            from margin_api.middleware.rate_limit import configure_limiter, limiter

            configure_limiter(redis_url="redis://localhost:6379", enabled=True)
            assert limiter.enabled is False


class TestResetLimiter:
    def test_reset_disables_limiter(self):
        from margin_api.middleware.rate_limit import limiter, reset_limiter

        limiter.enabled = True
        reset_limiter()
        assert limiter.enabled is False
