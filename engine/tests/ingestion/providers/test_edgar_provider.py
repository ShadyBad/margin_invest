"""Tests for SEC EDGAR data provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
from margin_engine.ingestion.types import DataCategory


def _make_response(json_data=None, text_data=None, success=True):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.is_success = success
    resp.raise_for_status = MagicMock()
    if not success:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    if json_data is not None:
        resp.json.return_value = json_data
    if text_data is not None:
        resp.text = text_data
    return resp


CIK_MAP_RESPONSE = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
}


class TestProviderInfo:
    def test_name(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.name == "edgar"

    def test_does_not_require_api_key(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.requires_api_key is False

    def test_supported_categories(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert set(provider.info.supported_categories) == {
            DataCategory.FUNDAMENTALS,
            DataCategory.INSIDER,
            DataCategory.INSTITUTIONAL,
        }

    def test_rate_limit(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider.info.requests_per_minute == 600

    def test_category_priorities(self):
        provider = EDGARProvider(user_agent="Test test@example.com")
        cp = provider.info.category_priorities
        assert cp is not None
        assert cp[DataCategory.FUNDAMENTALS] == 2
        assert cp[DataCategory.INSIDER] == 10
        assert cp[DataCategory.INSTITUTIONAL] == 10

    def test_empty_user_agent_raises(self):
        with pytest.raises(ValueError, match="User-Agent"):
            EDGARProvider(user_agent="")


class TestCIKMapping:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_lookup(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        cik = provider._get_cik("AAPL")

        assert cik == "0000320193"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_zero_padded_to_10_digits(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        cik = provider._get_cik("MSFT")

        assert len(cik) == 10
        assert cik == "0000789019"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_case_insensitive(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        assert provider._get_cik("aapl") == "0000320193"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_unknown_ticker_raises(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        with pytest.raises(ValueError, match="No CIK found"):
            provider._get_cik("ZZZZ")

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_cik_map_cached(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        provider._get_cik("AAPL")
        provider._get_cik("MSFT")

        # Only one HTTP call for the CIK map, not two
        assert mock_get.call_count == 1

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_company_name_lookup(self, mock_get):
        mock_get.return_value = _make_response(json_data=CIK_MAP_RESPONSE)

        provider = EDGARProvider(user_agent="Test test@example.com")
        name = provider._get_company_name("AAPL")

        assert name == "Apple Inc."
