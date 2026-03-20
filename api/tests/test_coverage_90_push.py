"""Coverage push to 90%: macro_data_client, admin routes, CLI functions.

Targets:
1. data/macro_data_client.py - fetch_yield_curve_slope, fetch_credit_spread, fetch_vix
2. routes/admin.py - pipeline/trigger, scoring/trigger, redis/health, redis/flush-jobs,
   ml/train, verify_admin_key helper
3. cli.py - run_price_backfill, run_edgar_backfill_cmd, run_edgar_reparse_cmd,
   run_universe_activate, run_backfill_country, run_pipeline, run_weight_tune,
   main() dispatcher branches
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# 1. macro_data_client.py - fetch_yield_curve_slope, fetch_credit_spread, fetch_vix
# =============================================================================


class TestFetchYieldCurveSlope:
    """Tests for fetch_yield_curve_slope."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from margin_api.data import macro_data_client

        macro_data_client._cache.clear()
        yield
        macro_data_client._cache.clear()

    @pytest.mark.asyncio
    async def test_returns_float_on_success(self):
        import httpx
        from margin_api.data.macro_data_client import fetch_yield_curve_slope

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        # DGS10 = 4.5, DGS2 = 4.0 => slope = 0.5
        mock_response.json = MagicMock(
            side_effect=[
                {"observations": [{"value": "4.5"}]},
                {"observations": [{"value": "4.0"}]},
            ]
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                result = await fetch_yield_curve_slope()

        assert isinstance(result, float)
        assert abs(result - 0.5) < 1e-9

    @pytest.mark.asyncio
    async def test_fallback_on_no_api_key(self):
        from margin_api.data.macro_data_client import fetch_yield_curve_slope

        env_without_key = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            result = await fetch_yield_curve_slope()

        assert result == 1.0

    @pytest.mark.asyncio
    async def test_fallback_on_http_error(self):
        import httpx
        from margin_api.data.macro_data_client import fetch_yield_curve_slope

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                result = await fetch_yield_curve_slope()

        assert result == 1.0

    @pytest.mark.asyncio
    async def test_caches_result(self):
        import httpx
        from margin_api.data.macro_data_client import fetch_yield_curve_slope

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            side_effect=[
                {"observations": [{"value": "3.0"}]},
                {"observations": [{"value": "2.0"}]},
            ]
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                r1 = await fetch_yield_curve_slope()
                r2 = await fetch_yield_curve_slope()

        assert r1 == r2
        # Cache hit: only 2 HTTP calls (DGS10+DGS2) on first call, not 4
        assert mock_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_cache_bypass_after_expiry(self):
        import httpx
        from margin_api.data import macro_data_client
        from margin_api.data.macro_data_client import fetch_yield_curve_slope

        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock(spec=httpx.Response)
            r.raise_for_status = MagicMock()
            # First two calls: DGS10=3.5, DGS2=2.5 => 1.0
            # Next two calls: DGS10=5.0, DGS2=3.0 => 2.0
            vals = ["3.5", "2.5", "5.0", "3.0"]
            r.json = MagicMock(return_value={"observations": [{"value": vals[call_count[0] - 1]}]})
            return r

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                await fetch_yield_curve_slope()
                # Expire the cache
                for key in macro_data_client._cache:
                    val, _ = macro_data_client._cache[key]
                    macro_data_client._cache[key] = (val, time.time() - 1)
                r2 = await fetch_yield_curve_slope()

        assert r2 == 2.0  # 5.0 - 3.0


class TestFetchCreditSpread:
    """Tests for fetch_credit_spread."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from margin_api.data import macro_data_client

        macro_data_client._cache.clear()
        yield
        macro_data_client._cache.clear()

    @pytest.mark.asyncio
    async def test_returns_float_on_success(self):
        import httpx
        from margin_api.data.macro_data_client import fetch_credit_spread

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"observations": [{"value": "1.75"}]})
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                result = await fetch_credit_spread()

        assert isinstance(result, float)
        assert abs(result - 1.75) < 1e-9

    @pytest.mark.asyncio
    async def test_fallback_on_no_api_key(self):
        from margin_api.data.macro_data_client import fetch_credit_spread

        env_without_key = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            result = await fetch_credit_spread()

        assert result == 2.0

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        from margin_api.data.macro_data_client import fetch_credit_spread

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("API down"))

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                result = await fetch_credit_spread()

        assert result == 2.0

    @pytest.mark.asyncio
    async def test_caches_result(self):
        import httpx
        from margin_api.data.macro_data_client import fetch_credit_spread

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"observations": [{"value": "2.5"}]})
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                r1 = await fetch_credit_spread()
                r2 = await fetch_credit_spread()

        assert r1 == r2 == 2.5
        # Cache hit on second call
        assert mock_client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_cache_bypass_after_expiry(self):
        import httpx
        from margin_api.data import macro_data_client
        from margin_api.data.macro_data_client import fetch_credit_spread

        call_count = [0]

        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock(spec=httpx.Response)
            r.raise_for_status = MagicMock()
            val = "1.5" if call_count[0] == 1 else "3.0"
            r.json = MagicMock(return_value={"observations": [{"value": val}]})
            return r

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get

        with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):
            with patch(
                "margin_api.data.macro_data_client.httpx.AsyncClient", return_value=mock_client
            ):
                await fetch_credit_spread()
                for key in macro_data_client._cache:
                    val, _ = macro_data_client._cache[key]
                    macro_data_client._cache[key] = (val, time.time() - 1)
                r2 = await fetch_credit_spread()

        assert r2 == 3.0


class TestFetchVix:
    """Tests for fetch_vix.

    yfinance is imported inside fetch_vix as `import yfinance as yf`, so we
    patch it via sys.modules rather than as a module attribute.
    """

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from margin_api.data import macro_data_client

        macro_data_client._cache.clear()
        yield
        macro_data_client._cache.clear()

    def _make_mock_yf(self, close_value: float):
        import pandas as pd

        mock_yf = MagicMock()
        df = pd.DataFrame({"Close": [close_value]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_yf.Ticker.return_value = mock_ticker
        return mock_yf

    @pytest.mark.asyncio
    async def test_returns_float_on_success(self):
        from margin_api.data.macro_data_client import fetch_vix

        mock_yf = self._make_mock_yf(18.5)
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = await fetch_vix()

        assert isinstance(result, float)
        assert result == 18.5

    @pytest.mark.asyncio
    async def test_fallback_on_empty_history(self):
        from margin_api.data.macro_data_client import fetch_vix

        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = MagicMock(empty=True)
        mock_yf.Ticker.return_value = mock_ticker

        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = await fetch_vix()

        assert result == 20.0

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        from margin_api.data.macro_data_client import fetch_vix

        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = RuntimeError("yfinance broke")

        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = await fetch_vix()

        assert result == 20.0

    @pytest.mark.asyncio
    async def test_caches_result(self):
        from margin_api.data.macro_data_client import fetch_vix

        mock_yf = self._make_mock_yf(22.0)
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            r1 = await fetch_vix()
            r2 = await fetch_vix()

        assert r1 == r2 == 22.0
        # Only one Ticker lookup on first call, cache hit on second
        mock_yf.Ticker.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_bypass_after_expiry(self):
        import pandas as pd
        from margin_api.data import macro_data_client
        from margin_api.data.macro_data_client import fetch_vix

        call_count = [0]
        mock_yf = MagicMock()

        def make_ticker(sym):
            call_count[0] += 1
            t = MagicMock()
            val = 15.0 if call_count[0] == 1 else 30.0
            t.history.return_value = pd.DataFrame({"Close": [val]})
            return t

        mock_yf.Ticker.side_effect = make_ticker

        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            await fetch_vix()
            for key in macro_data_client._cache:
                val, _ = macro_data_client._cache[key]
                macro_data_client._cache[key] = (val, time.time() - 1)
            r2 = await fetch_vix()

        assert r2 == 30.0


# =============================================================================
# 2. routes/admin.py - uncovered endpoints
# =============================================================================


def _make_admin_client(app):
    from fastapi.testclient import TestClient
    from margin_api.db.models import User, UserRole
    from margin_api.deps import get_admin_user

    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    app.dependency_overrides[get_admin_user] = lambda: user
    return TestClient(app)


class TestPipelineTrigger:
    def setup_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def teardown_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def test_pipeline_trigger_enqueues_job(self):
        from margin_api.app import create_app

        mock_job = MagicMock()
        mock_job.job_id = "orchestrate-abc"
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/pipeline/trigger")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "orchestrate_ingest"
        assert data["job_id"] == "orchestrate-abc"

    def test_pipeline_trigger_redis_failure(self):
        from margin_api.app import create_app

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/pipeline/trigger")

        assert resp.status_code == 503

    def test_pipeline_trigger_requires_auth(self):
        from fastapi.testclient import TestClient
        from margin_api.app import create_app

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/pipeline/trigger")
        assert resp.status_code == 401


class TestScoringTrigger:
    def setup_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def teardown_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def test_scoring_trigger_enqueues_job(self):
        from margin_api.app import create_app

        mock_job = MagicMock()
        mock_job.job_id = "scoring-xyz"
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/scoring/trigger")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "full_score_v3"
        assert data["job_id"] == "scoring-xyz"

    def test_scoring_trigger_redis_failure(self):
        from margin_api.app import create_app

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/scoring/trigger")

        assert resp.status_code == 503


class TestRedisHealth:
    def setup_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def teardown_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def test_redis_health_connected(self):
        from margin_api.app import create_app

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.zrangebyscore = AsyncMock(return_value=[b"job-1", b"job-2"])
        mock_redis.keys = AsyncMock(
            side_effect=[
                [],  # in-progress keys
                [],  # result keys
            ]
        )
        mock_redis.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_redis),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert data["queued_count"] == 2
        assert "job-1" in data["queued_jobs"]

    def test_redis_health_error(self):
        from margin_api.app import create_app

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.aioredis.from_url",
                side_effect=ConnectionError("Redis unavailable"),
            ),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"

    def test_redis_health_no_pong(self):
        from margin_api.app import create_app

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=False)
        mock_redis.zrangebyscore = AsyncMock(return_value=[])
        mock_redis.keys = AsyncMock(side_effect=[[], []])
        mock_redis.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_redis),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "no_pong"

    def test_redis_health_with_in_progress(self):
        from margin_api.app import create_app

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.zrangebyscore = AsyncMock(return_value=[])
        mock_redis.keys = AsyncMock(
            side_effect=[
                [b"arq:in-progress:job-999"],  # in-progress
                [b"arq:result:job-888"],  # results
            ]
        )
        mock_redis.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_redis),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "job-999" in data["in_progress"]


class TestRedisFlushJobs:
    def setup_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def teardown_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def test_flush_jobs_success(self):
        from margin_api.app import create_app

        mock_redis = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[b"job-abc", b"job-xyz"])
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.keys = AsyncMock(
            side_effect=[
                [b"arq:in-progress:job-abc"],
                [b"arq:result:job-xyz"],
            ]
        )
        mock_redis.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_redis),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "flushed"
        assert "job-abc" in data["removed_jobs"]
        assert "job-xyz" in data["removed_jobs"]

    def test_flush_jobs_error(self):
        from margin_api.app import create_app

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.aioredis.from_url",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"

    def test_flush_jobs_empty_queue(self):
        from margin_api.app import create_app

        mock_redis = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.keys = AsyncMock(side_effect=[[], []])
        mock_redis.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_redis),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "flushed"
        assert data["removed_jobs"] == []


class TestMLTrain:
    def setup_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def teardown_method(self):
        from margin_api.config import get_settings

        get_settings.cache_clear()

    def test_ml_train_enqueues_job(self):
        from margin_api.app import create_app

        mock_job = MagicMock()
        mock_job.job_id = "train-ml-001"
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/ml/train")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "train_ml_models"
        assert data["job_id"] == "train-ml-001"

    def test_ml_train_redis_failure(self):
        from margin_api.app import create_app

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_admin_client(app)
            resp = client.post("/api/v1/admin/ml/train")

        assert resp.status_code == 503


class TestVerifyAdminKey:
    def test_raises_when_key_not_configured(self):
        from fastapi import HTTPException
        from margin_api.config import get_settings
        from margin_api.routes.admin import _verify_admin_key

        get_settings.cache_clear()
        try:
            env_without_key = {k: v for k, v in os.environ.items() if k != "MARGIN_ADMIN_KEY"}
            with patch.dict(os.environ, env_without_key, clear=True):
                get_settings.cache_clear()
                with pytest.raises(HTTPException) as exc_info:
                    _verify_admin_key(x_admin_key="any-key")
            assert exc_info.value.status_code == 503
        finally:
            get_settings.cache_clear()

    def test_raises_when_key_invalid(self):
        from fastapi import HTTPException
        from margin_api.config import get_settings
        from margin_api.routes.admin import _verify_admin_key

        get_settings.cache_clear()
        try:
            with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "correct-key"}):
                get_settings.cache_clear()
                with pytest.raises(HTTPException) as exc_info:
                    _verify_admin_key(x_admin_key="wrong-key")
            assert exc_info.value.status_code == 403
        finally:
            get_settings.cache_clear()

    def test_passes_when_key_matches(self):
        from margin_api.config import get_settings
        from margin_api.routes.admin import _verify_admin_key

        get_settings.cache_clear()
        try:
            with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "correct-key"}):
                get_settings.cache_clear()
                # Should not raise
                _verify_admin_key(x_admin_key="correct-key")
        finally:
            get_settings.cache_clear()


# =============================================================================
# 3. cli.py - async functions and main() dispatcher
# =============================================================================


def _make_session_factory(mock_session):
    factory = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestRunPriceBackfill:
    def test_with_explicit_tickers(self):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.price_backfill.backfill_prices_for_tickers",
                    new_callable=AsyncMock,
                    return_value={"AAPL": 100, "MSFT": 200},
                ) as mock_backfill:
                    _run(run_price_backfill(tickers=["AAPL", "MSFT"], start_date="2020-01-01"))

        mock_backfill.assert_awaited_once()
        call_kwargs = mock_backfill.call_args.kwargs
        assert call_kwargs["tickers"] == ["AAPL", "MSFT"]
        assert call_kwargs["start_date"] == "2020-01-01"

    def test_fetches_tickers_from_db_when_none(self):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("GOOG",)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.price_backfill.backfill_prices_for_tickers",
                    new_callable=AsyncMock,
                    return_value={"AAPL": 50, "GOOG": 75},
                ) as mock_backfill:
                    _run(run_price_backfill(tickers=None, start_date="2020-01-01"))

        mock_backfill.assert_awaited_once()
        call_kwargs = mock_backfill.call_args.kwargs
        assert "AAPL" in call_kwargs["tickers"]
        assert "GOOG" in call_kwargs["tickers"]

    def test_returns_early_when_no_tickers_in_db(self):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.price_backfill.backfill_prices_for_tickers",
                    new_callable=AsyncMock,
                ) as mock_backfill:
                    _run(run_price_backfill(tickers=None))

        mock_backfill.assert_not_awaited()

    def test_prints_summary(self, capsys):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.price_backfill.backfill_prices_for_tickers",
                    new_callable=AsyncMock,
                    return_value={"AAPL": 100},
                ):
                    _run(run_price_backfill(tickers=["AAPL"]))

        captured = capsys.readouterr()
        assert "Price backfill complete" in captured.out
        assert "AAPL: 100 rows" in captured.out


class TestRunEdgarBackfillCmd:
    def test_runs_backfill_and_prints_summary(self, capsys):
        from margin_api.cli import run_edgar_backfill_cmd

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()
        summary = {"total": 100, "inserted": 95, "skipped": 3, "failed": 2}

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.backfill.run_edgar_backfill",
                    new_callable=AsyncMock,
                    return_value=summary,
                ) as mock_run:
                    _run(
                        run_edgar_backfill_cmd(
                            start_year=2020,
                            end_year=2024,
                            checkpoint_file=".test_checkpoint",
                            dry_run=False,
                        )
                    )

        mock_run.assert_awaited_once()
        captured = capsys.readouterr()
        assert "100 total" in captured.out
        assert "95 inserted" in captured.out

    def test_passes_dry_run_flag(self):
        from margin_api.cli import run_edgar_backfill_cmd

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()
        summary = {"total": 0, "inserted": 0, "skipped": 0, "failed": 0}

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.backfill.run_edgar_backfill",
                    new_callable=AsyncMock,
                    return_value=summary,
                ) as mock_run:
                    _run(run_edgar_backfill_cmd(dry_run=True))

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["dry_run"] is True


class TestRunEdgarReparseCmd:
    def test_runs_reparse_and_prints_summary(self, capsys):
        from margin_api.cli import run_edgar_reparse_cmd

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()
        summary = {"total": 50, "reparsed": 45, "failed": 3, "still_empty": 2}

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.backfill.reparse_empty_filings",
                    new_callable=AsyncMock,
                    return_value=summary,
                ):
                    _run(run_edgar_reparse_cmd())

        captured = capsys.readouterr()
        assert "50 empty filings" in captured.out
        assert "45 reparsed" in captured.out


class TestRunUniverseActivate:
    def test_activates_from_existing_config(self, tmp_path):
        from margin_api.cli import run_universe_activate

        fake_config = tmp_path / "universe.yaml"
        fake_config.write_text("tickers: [AAPL, MSFT]")

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        mock_snapshot = MagicMock()
        mock_snapshot.version = "1.0"
        mock_snapshot.ticker_count = 2
        mock_snapshot.config_hash = "abc123"

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=session_factory),
            patch(
                "margin_api.cli.activate_universe",
                new_callable=AsyncMock,
                return_value=mock_snapshot,
            ),
        ):
            _run(run_universe_activate(config_path=str(fake_config)))

    def test_exits_when_config_path_not_found(self):
        from margin_api.cli import run_universe_activate

        with pytest.raises(SystemExit):
            _run(run_universe_activate(config_path="/nonexistent/path/universe.yaml"))

    def test_uses_default_config_exits_if_missing(self):
        from margin_api.cli import run_universe_activate

        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SystemExit):
                _run(run_universe_activate(config_path=None))


class TestRunBackfillCountry:
    def test_skips_when_no_assets_missing_country(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch("margin_api.cli.YFinanceProvider"):
                        _run(run_backfill_country())

    def test_updates_country_for_assets(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        mock_asset = MagicMock()
        mock_asset.ticker = "AAPL"
        mock_asset.id = 1

        mock_db_asset = MagicMock()
        mock_db_asset.country = None

        call_count = [0]
        mock_first_result = MagicMock()
        mock_first_result.scalars.return_value.all.return_value = [mock_asset]
        mock_second_result = MagicMock()
        mock_second_result.scalar_one.return_value = mock_db_asset

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_first_result
            return mock_second_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        mock_info_result = MagicMock(success=True, raw_data={"country": "United States"})
        mock_provider_instance.fetch_info.return_value = mock_info_result

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        _run(run_backfill_country())

        assert mock_db_asset.country == "United States"

    def test_handles_provider_exception_gracefully(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        mock_asset = MagicMock()
        mock_asset.ticker = "FAIL"
        mock_asset.id = 99

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_asset]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        mock_provider_instance.fetch_info.side_effect = RuntimeError("Provider error")

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        _run(run_backfill_country())

    def test_skips_when_no_country_in_info(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        mock_asset = MagicMock()
        mock_asset.ticker = "AAPL"
        mock_asset.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_asset]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        # Returns success but no country field
        mock_info_result = MagicMock(success=True, raw_data={})
        mock_provider_instance.fetch_info.return_value = mock_info_result

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        _run(run_backfill_country())


class TestRunPipeline:
    def test_calls_seed_then_score(self):
        from margin_api.cli import run_pipeline

        with patch("margin_api.cli.run_seed", new_callable=AsyncMock) as mock_seed:
            with patch("margin_api.cli.run_scoring", new_callable=AsyncMock) as mock_score:
                _run(run_pipeline(tickers=["AAPL", "MSFT"]))

        mock_seed.assert_awaited_once_with(tickers=["AAPL", "MSFT"])
        mock_score.assert_awaited_once_with(tickers=["AAPL", "MSFT"])

    def test_calls_seed_then_score_with_none(self):
        from margin_api.cli import run_pipeline

        with patch("margin_api.cli.run_seed", new_callable=AsyncMock) as mock_seed:
            with patch("margin_api.cli.run_scoring", new_callable=AsyncMock) as mock_score:
                _run(run_pipeline(tickers=None))

        mock_seed.assert_awaited_once_with(tickers=None)
        mock_score.assert_awaited_once_with(tickers=None)


class TestRunWeightTune:
    def test_dry_run_prints_factors_without_optimizing(self, capsys):
        from margin_api.cli import run_weight_tune

        mock_optuna = MagicMock()
        mock_track_factors = {
            "A": ["roic", "fcf_margin"],
            "B": ["ev_fcf", "pe_ratio"],
            "C": ["rev_growth"],
        }

        with patch.dict(sys.modules, {"optuna": mock_optuna}):
            with patch("margin_engine.tuning.weight_optimizer.TRACK_FACTORS", mock_track_factors):
                run_weight_tune(track="ALL", n_trials=10, metric="sharpe", dry_run=True)

        captured = capsys.readouterr()
        assert "Dry run complete" in captured.out

    def test_single_track_dry_run(self, capsys):
        from margin_api.cli import run_weight_tune

        mock_optuna = MagicMock()
        mock_track_factors = {
            "A": ["roic", "fcf_margin"],
            "B": ["ev_fcf"],
            "C": ["rev_growth"],
        }

        with patch.dict(sys.modules, {"optuna": mock_optuna}):
            with patch("margin_engine.tuning.weight_optimizer.TRACK_FACTORS", mock_track_factors):
                run_weight_tune(track="A", n_trials=5, metric="sharpe", dry_run=True)

        captured = capsys.readouterr()
        assert "Dry run complete" in captured.out

    def test_exits_on_unknown_track(self):
        from margin_api.cli import run_weight_tune

        mock_track_factors = {"A": ["roic"], "B": ["ev_fcf"], "C": ["rev_growth"]}

        with patch("margin_engine.tuning.weight_optimizer.TRACK_FACTORS", mock_track_factors):
            with pytest.raises(SystemExit):
                run_weight_tune(track="Z", dry_run=False)

    def test_exits_when_optuna_not_installed(self):
        from margin_api.cli import run_weight_tune

        original = sys.modules.get("optuna")
        sys.modules["optuna"] = None
        try:
            with pytest.raises((SystemExit, ImportError, TypeError)):
                run_weight_tune(track="ALL", n_trials=1, dry_run=False)
        finally:
            if original is None:
                del sys.modules["optuna"]
            else:
                sys.modules["optuna"] = original


class TestMainDispatcher:
    def test_seed_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "seed", "--tickers", "AAPL"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_score_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "score", "--tickers", "AAPL"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_score_v3_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "score-v3", "--cape", "28.0"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_score_v4_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "score-v4"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_score_universe_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "score-universe", "--limit", "10"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_pipeline_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "pipeline"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_backfill_country_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "backfill-country"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_backfill_13f_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "backfill-13f", "--start-year", "2015"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_price_backfill_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(
                sys,
                "argv",
                ["margin-cli", "price-backfill", "--start-date", "2020-01-01"],
            ):
                main()
        mock_asyncio.run.assert_called_once()

    def test_edgar_backfill_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(
                sys,
                "argv",
                ["margin-cli", "edgar-backfill", "--start-year", "2020", "--dry-run"],
            ):
                main()
        mock_asyncio.run.assert_called_once()

    def test_edgar_reparse_command_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(sys, "argv", ["margin-cli", "edgar-reparse"]):
                main()
        mock_asyncio.run.assert_called_once()

    def test_correlations_showcase_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(
                sys,
                "argv",
                ["margin-cli", "correlations", "--showcase", "--tickers", "AAPL", "MSFT"],
            ):
                main()
        mock_asyncio.run.assert_called_once()

    def test_correlations_no_showcase_exits(self):
        from margin_api.cli import main

        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["margin-cli", "correlations"]):
                main()

    def test_universe_generate_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.run_universe_generate") as mock_gen:
            with patch.object(sys, "argv", ["margin-cli", "universe", "generate"]):
                main()
        mock_gen.assert_called_once()

    def test_universe_activate_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            with patch.object(
                sys,
                "argv",
                ["margin-cli", "universe", "activate", "--config", "/fake/universe.yaml"],
            ):
                main()
        mock_asyncio.run.assert_called_once()

    def test_universe_no_subcommand_exits(self):
        from margin_api.cli import main

        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["margin-cli", "universe"]):
                main()

    def test_unknown_command_exits(self):
        from margin_api.cli import main

        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["margin-cli", "unknown-command"]):
                main()

    def test_weight_tune_dry_run_dispatches(self):
        from margin_api.cli import main

        with patch("margin_api.cli.run_weight_tune") as mock_tune:
            with patch.object(
                sys,
                "argv",
                ["margin-cli", "weight-tune", "A", "--n-trials", "5", "--dry-run"],
            ):
                main()
        mock_tune.assert_called_once()

    def test_no_command_exits(self):
        from margin_api.cli import main

        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["margin-cli"]):
                main()


class TestRunBackfill13F:
    def test_processes_curated_funds(self):
        from margin_api.cli import run_backfill_13f

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        mock_mgr = MagicMock()
        mock_mgr.id = 1
        mock_mgr_result = MagicMock()
        mock_mgr_result.scalar_one.return_value = mock_mgr

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_mgr_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        mock_service = AsyncMock()
        mock_service.upsert_managers = AsyncMock()
        mock_service.is_filing_new = AsyncMock(return_value=False)
        mock_service_cls = MagicMock(return_value=mock_service)

        mock_edgar = MagicMock()
        mock_edgar.get_13f_submissions.return_value = {}
        mock_edgar.extract_13f_filings.return_value = []

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.thirteenf_ingest.ThirteenFIngestService",
                    mock_service_cls,
                ):
                    with patch(
                        "margin_engine.ingestion.providers.edgar_provider.EDGARProvider",
                        return_value=mock_edgar,
                    ):
                        _run(run_backfill_13f(start_year=2020, max_managers=1))

    def test_curated_funds_list_not_empty(self):
        from margin_api import cli as cli_mod

        assert len(cli_mod.CURATED_FUNDS) >= 1
        assert "cik" in cli_mod.CURATED_FUNDS[0]


class TestRunCorrelationsShowcase:
    def test_returns_early_with_insufficient_data(self):
        from margin_api.cli import run_correlations_showcase

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                _run(run_correlations_showcase(tickers=["AAPL"]))


class TestLoadAndPredictML:
    def test_returns_empty_when_no_cluster_model_data(self):
        from margin_api.cli import _load_and_predict_ml

        ml_run = MagicMock()
        ml_run.model_qualifies = True
        ml_run.cluster_model_data = None

        result = _run(_load_and_predict_ml(ml_run, []))

        assert result["model_qualifies"] is True
        assert result["alphas"] == {}
        assert result["vae_means"] == {}
        assert result["vae_variances"] == {}

    def test_returns_empty_on_bad_cluster_bytes(self):
        from margin_api.cli import _load_and_predict_ml

        ml_run = MagicMock()
        ml_run.model_qualifies = True
        # Provide bytes that are clearly not valid serialized data
        ml_run.cluster_model_data = b"this-is-not-valid-cluster-data-bytes-xyz"

        result = _run(_load_and_predict_ml(ml_run, []))

        # Should handle deserialization failure gracefully
        assert result["alphas"] == {}
