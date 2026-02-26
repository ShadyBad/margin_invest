"""Tests for the CUSIP resolution service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from margin_engine.services.cusip_resolver import (
    CUSIPResolver,
    Holding,
    KnownAsset,
    ResolvedSecurity,
)


class TestCacheHit:
    """Test 1: resolve_from_cache returns cached entry."""

    def test_cache_hit_returns_resolved_security(self) -> None:
        resolver = CUSIPResolver()
        entry = ResolvedSecurity(
            cusip="037833100",
            ticker="AAPL",
            figi="BBG000B9XRY4",
            issuer_name="APPLE INC",
            resolution_method="openfigi",
        )
        resolver.seed_cache([entry])

        result = resolver.resolve_from_cache("037833100")

        assert result is not None
        assert result.cusip == "037833100"
        assert result.ticker == "AAPL"
        assert result.figi == "BBG000B9XRY4"
        assert result.issuer_name == "APPLE INC"
        assert result.resolution_method == "openfigi"


class TestCacheMiss:
    """Test 2: resolve_from_cache returns None for unknown CUSIP."""

    def test_cache_miss_returns_none(self) -> None:
        resolver = CUSIPResolver()

        result = resolver.resolve_from_cache("000000000")

        assert result is None

    def test_empty_cache_returns_none(self) -> None:
        resolver = CUSIPResolver()
        result = resolver.resolve_from_cache("037833100")
        assert result is None


class TestParseOpenfigiSuccess:
    """Test 3: _parse_openfigi_response parses successful responses."""

    def test_parse_single_success(self) -> None:
        resolver = CUSIPResolver()
        batch = [Holding(cusip="037833100", issuer_name="APPLE INC")]
        response_data = [
            {
                "data": [
                    {
                        "ticker": "AAPL",
                        "figi": "BBG000B9XRY4",
                        "name": "APPLE INC",
                    }
                ]
            }
        ]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert "037833100" in results
        resolved = results["037833100"]
        assert resolved.ticker == "AAPL"
        assert resolved.figi == "BBG000B9XRY4"
        assert resolved.issuer_name == "APPLE INC"
        assert resolved.resolution_method == "openfigi"

    def test_parse_multiple_success(self) -> None:
        resolver = CUSIPResolver()
        batch = [
            Holding(cusip="037833100", issuer_name="APPLE INC"),
            Holding(cusip="594918104", issuer_name="MICROSOFT CORP"),
        ]
        response_data = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]},
            {"data": [{"ticker": "MSFT", "figi": "BBG000BPH459", "name": "MICROSOFT CORP"}]},
        ]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert len(results) == 2
        assert results["037833100"].ticker == "AAPL"
        assert results["594918104"].ticker == "MSFT"

    def test_parse_uses_first_match_when_multiple_data_entries(self) -> None:
        resolver = CUSIPResolver()
        batch = [Holding(cusip="037833100", issuer_name="APPLE INC")]
        response_data = [
            {
                "data": [
                    {"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"},
                    {"ticker": "AAPL.L", "figi": "BBG000BBLLL0", "name": "APPLE INC (LSE)"},
                ]
            }
        ]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert results["037833100"].ticker == "AAPL"
        assert results["037833100"].figi == "BBG000B9XRY4"


class TestParseOpenfigiUnresolved:
    """Test 4: _parse_openfigi_response handles warnings/unresolved entries."""

    def test_warning_entry_is_skipped(self) -> None:
        resolver = CUSIPResolver()
        batch = [Holding(cusip="000000000", issuer_name="UNKNOWN CORP")]
        response_data = [{"warning": "No identifier found."}]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert len(results) == 0

    def test_empty_data_is_skipped(self) -> None:
        resolver = CUSIPResolver()
        batch = [Holding(cusip="000000000", issuer_name="UNKNOWN CORP")]
        response_data = [{"data": []}]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert len(results) == 0

    def test_mixed_success_and_warning(self) -> None:
        resolver = CUSIPResolver()
        batch = [
            Holding(cusip="037833100", issuer_name="APPLE INC"),
            Holding(cusip="000000000", issuer_name="UNKNOWN CORP"),
        ]
        response_data = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]},
            {"warning": "No identifier found."},
        ]

        results = resolver._parse_openfigi_response(response_data, batch)

        assert len(results) == 1
        assert "037833100" in results
        assert "000000000" not in results


class TestFuzzyExactMatch:
    """Test 5: _fuzzy_name_match with exact (case-insensitive) match."""

    def test_exact_case_insensitive_match(self) -> None:
        known = [KnownAsset(ticker="AAPL", name="Apple Inc")]
        result = CUSIPResolver._fuzzy_name_match("APPLE INC", known)

        assert result is not None
        assert result.ticker == "AAPL"

    def test_exact_match_same_case(self) -> None:
        known = [KnownAsset(ticker="AAPL", name="Apple Inc")]
        result = CUSIPResolver._fuzzy_name_match("Apple Inc", known)

        assert result is not None
        assert result.ticker == "AAPL"


class TestFuzzyPartialMatch:
    """Test 6: _fuzzy_name_match with partial substring match."""

    def test_issuer_contains_asset_name(self) -> None:
        known = [KnownAsset(ticker="AAPL", name="Apple")]
        result = CUSIPResolver._fuzzy_name_match("APPLE INC COM STK", known)

        assert result is not None
        assert result.ticker == "AAPL"

    def test_asset_name_contains_issuer(self) -> None:
        known = [KnownAsset(ticker="MSFT", name="Microsoft Corporation")]
        result = CUSIPResolver._fuzzy_name_match("Microsoft", known)

        assert result is not None
        assert result.ticker == "MSFT"

    def test_partial_match_mid_string(self) -> None:
        known = [KnownAsset(ticker="NVDA", name="NVIDIA")]
        result = CUSIPResolver._fuzzy_name_match("NVIDIA CORP CL A", known)

        assert result is not None
        assert result.ticker == "NVDA"


class TestFuzzyNoMatch:
    """Test 7: _fuzzy_name_match returns None when nothing matches."""

    def test_no_match(self) -> None:
        known = [
            KnownAsset(ticker="AAPL", name="Apple Inc"),
            KnownAsset(ticker="MSFT", name="Microsoft Corporation"),
        ]
        result = CUSIPResolver._fuzzy_name_match("TOTALLY UNKNOWN CORP", known)

        assert result is None

    def test_empty_known_assets(self) -> None:
        result = CUSIPResolver._fuzzy_name_match("APPLE INC", [])
        assert result is None

    def test_empty_issuer_name(self) -> None:
        known = [KnownAsset(ticker="AAPL", name="Apple Inc")]
        result = CUSIPResolver._fuzzy_name_match("", known)
        assert result is None


class TestResolveBatchWithMockedHttpx:
    """Test 8: resolve_batch end-to-end with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_resolve_batch_uses_cache_first(self) -> None:
        resolver = CUSIPResolver()
        cached = ResolvedSecurity(
            cusip="037833100",
            ticker="AAPL",
            figi="BBG000B9XRY4",
            issuer_name="APPLE INC",
            resolution_method="openfigi",
        )
        resolver.seed_cache([cached])

        holdings = [Holding(cusip="037833100", issuer_name="APPLE INC")]
        results = await resolver.resolve_batch(holdings)

        assert results["037833100"].ticker == "AAPL"
        assert results["037833100"].resolution_method == "openfigi"

    @pytest.mark.asyncio
    async def test_resolve_batch_calls_openfigi_for_uncached(self) -> None:
        resolver = CUSIPResolver(openfigi_api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("margin_engine.services.cusip_resolver.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            holdings = [Holding(cusip="037833100", issuer_name="APPLE INC")]
            results = await resolver.resolve_batch(holdings)

        assert "037833100" in results
        assert results["037833100"].ticker == "AAPL"
        assert results["037833100"].resolution_method == "openfigi"

        # Verify the API key was sent in headers
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["headers"]["X-OPENFIGI-APIKEY"] == "test-key"

    @pytest.mark.asyncio
    async def test_resolve_batch_falls_back_to_fuzzy_match(self) -> None:
        resolver = CUSIPResolver()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"warning": "No identifier found."}]
        mock_response.raise_for_status = MagicMock()

        with patch("margin_engine.services.cusip_resolver.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            holdings = [Holding(cusip="037833100", issuer_name="APPLE INC")]
            known = [KnownAsset(ticker="AAPL", name="Apple Inc")]
            results = await resolver.resolve_batch(holdings, known_assets=known)

        assert results["037833100"].ticker == "AAPL"
        assert results["037833100"].resolution_method == "name_match"

    @pytest.mark.asyncio
    async def test_resolve_batch_marks_unresolved_when_all_fail(self) -> None:
        resolver = CUSIPResolver()

        mock_response = MagicMock()
        mock_response.json.return_value = [{"warning": "No identifier found."}]
        mock_response.raise_for_status = MagicMock()

        with patch("margin_engine.services.cusip_resolver.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            holdings = [Holding(cusip="000000000", issuer_name="TOTALLY UNKNOWN")]
            results = await resolver.resolve_batch(holdings)

        assert results["000000000"].ticker is None
        assert results["000000000"].resolution_method == "unresolved"

    @pytest.mark.asyncio
    async def test_resolve_batch_caches_results(self) -> None:
        resolver = CUSIPResolver()

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"data": [{"ticker": "AAPL", "figi": "BBG000B9XRY4", "name": "APPLE INC"}]},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("margin_engine.services.cusip_resolver.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            holdings = [Holding(cusip="037833100", issuer_name="APPLE INC")]
            await resolver.resolve_batch(holdings)

        # Second call should use cache — no HTTP needed
        cached = resolver.resolve_from_cache("037833100")
        assert cached is not None
        assert cached.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_resolve_batch_handles_http_error_gracefully(self) -> None:
        resolver = CUSIPResolver()

        with patch("margin_engine.services.cusip_resolver.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=httpx.Request("POST", OPENFIGI_URL),
                response=httpx.Response(429),
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            holdings = [Holding(cusip="037833100", issuer_name="APPLE INC")]
            known = [KnownAsset(ticker="AAPL", name="Apple Inc")]
            results = await resolver.resolve_batch(holdings, known_assets=known)

        # Should fall back to fuzzy match
        assert results["037833100"].ticker == "AAPL"
        assert results["037833100"].resolution_method == "name_match"


OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
