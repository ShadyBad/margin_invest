# SEC EDGAR Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SEC EDGAR as a data provider for fundamentals (XBRL), insider transactions (Form 4), and institutional holdings (13F), with per-category priority support in the registry.

**Architecture:** Single `EDGARProvider` class using httpx for HTTP calls and xml.etree.ElementTree for Form 4/13F XML parsing. New `category_priorities` field on `ProviderInfo` lets one provider have different priorities per category. CIK mapping is lazy-loaded from SEC's public ticker list.

**Tech Stack:** httpx (existing dependency), xml.etree.ElementTree (stdlib), re (stdlib)

---

### Task 1: Per-Category Priority Support

Add `category_priorities` to `ProviderInfo` and update the registry to use it.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/types.py:37-53`
- Modify: `engine/src/margin_engine/ingestion/registry.py:89-107`
- Modify: `engine/tests/ingestion/test_registry.py`

**Step 1: Write the failing tests**

Add a new test class to the bottom of `engine/tests/ingestion/test_registry.py`:

```python
# ---------------------------------------------------------------------------
# Tests: per-category priority
# ---------------------------------------------------------------------------


class TestPerCategoryPriority:
    def test_category_priorities_override_base_priority(self):
        """Provider with category_priorities uses per-category values."""
        registry = ProviderRegistry()
        provider = FakeProvider(
            "multi",
            [DataCategory.FUNDAMENTALS, DataCategory.INSIDER],
            priority=10,
        )
        # Override: fundamentals at priority 2, insider stays at base 10
        provider._info = ProviderInfo(
            name="multi",
            supported_categories=[DataCategory.FUNDAMENTALS, DataCategory.INSIDER],
            requests_per_minute=60,
            requires_api_key=False,
            priority=10,
            category_priorities={DataCategory.FUNDAMENTALS: 2},
        )
        other = FakeProvider("other", [DataCategory.FUNDAMENTALS, DataCategory.INSIDER], priority=5)
        registry.register(provider)
        registry.register(other)

        # For FUNDAMENTALS, "multi" has effective priority 2 (below "other" at 5)
        fund_chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        assert [p.info.name for p in fund_chain] == ["other", "multi"]

        # For INSIDER, "multi" has effective priority 10 (above "other" at 5)
        insider_chain = registry.get_fallback_chain(DataCategory.INSIDER)
        assert [p.info.name for p in insider_chain] == ["multi", "other"]

    def test_category_priorities_none_uses_base(self):
        """When category_priorities is None, base priority is used."""
        registry = ProviderRegistry()
        provider = FakeProvider("simple", [DataCategory.PRICE], priority=7)
        registry.register(provider)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 1
        assert chain[0].info.priority == 7

    def test_category_not_in_overrides_uses_base(self):
        """Category not in category_priorities dict falls back to base."""
        registry = ProviderRegistry()
        provider = FakeProvider("partial", [DataCategory.INSIDER, DataCategory.INSTITUTIONAL], priority=10)
        provider._info = ProviderInfo(
            name="partial",
            supported_categories=[DataCategory.INSIDER, DataCategory.INSTITUTIONAL],
            requests_per_minute=60,
            requires_api_key=False,
            priority=10,
            category_priorities={DataCategory.INSIDER: 15},
        )
        other = FakeProvider("other", [DataCategory.INSTITUTIONAL], priority=12)
        registry.register(provider)
        registry.register(other)

        # INSTITUTIONAL not in overrides -> uses base priority 10 (below other at 12)
        chain = registry.get_fallback_chain(DataCategory.INSTITUTIONAL)
        assert [p.info.name for p in chain] == ["other", "partial"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_registry.py::TestPerCategoryPriority -v`
Expected: FAIL — `ProviderInfo` does not accept `category_priorities`

**Step 3: Add category_priorities to ProviderInfo**

In `engine/src/margin_engine/ingestion/types.py`, add the field to `ProviderInfo`:

```python
class ProviderInfo(BaseModel):
    """Metadata describing a data provider's capabilities and constraints."""

    name: str
    """Unique provider name (e.g., 'yfinance', 'finnhub')."""

    supported_categories: list[DataCategory]
    """What data categories this provider can fetch."""

    requests_per_minute: int
    """Rate limit for this provider."""

    requires_api_key: bool
    """Whether an API key is needed to use this provider."""

    priority: int = 0
    """Higher values = preferred provider (used for fallback ordering)."""

    category_priorities: dict[DataCategory, int] | None = None
    """Optional per-category priority overrides.

    When set, the registry uses ``category_priorities.get(category)``
    for sorting. Falls back to the base ``priority`` when a category
    is not present in the dict or when ``category_priorities`` is None.
    """
```

**Step 4: Update get_fallback_chain to use per-category priority**

In `engine/src/margin_engine/ingestion/registry.py`, change the sort key in `get_fallback_chain`:

```python
    def get_fallback_chain(self, category: DataCategory) -> list[DataProvider]:
        """Get the ordered fallback chain for a data category.

        Returns providers sorted by priority (highest first).
        Excludes providers that require an API key but don't have one
        (or have an empty string key).
        """
        eligible: list[DataProvider] = []
        for provider in self._providers:
            info = provider.info
            if category not in info.supported_categories:
                continue
            if info.requires_api_key and not self._api_keys.get(info.name):
                continue
            eligible.append(provider)

        def _effective_priority(p: DataProvider) -> int:
            info = p.info
            if info.category_priorities is not None:
                return info.category_priorities.get(category, info.priority)
            return info.priority

        eligible.sort(key=_effective_priority, reverse=True)
        return eligible
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_registry.py -v`
Expected: ALL PASS (both new and existing tests)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/ingestion/types.py engine/src/margin_engine/ingestion/registry.py engine/tests/ingestion/test_registry.py
git commit -m "feat(engine): add per-category priority to ProviderInfo and registry"
```

---

### Task 2: EDGARProvider Skeleton + CIK Mapping

Create the provider file with constructor, info property, and CIK mapping logic.

**Files:**
- Create: `engine/src/margin_engine/ingestion/providers/edgar_provider.py`
- Create: `engine/tests/ingestion/providers/test_edgar_provider.py`

**Step 1: Write the failing tests**

Create `engine/tests/ingestion/providers/test_edgar_provider.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py::TestProviderInfo -v`
Expected: FAIL — module `edgar_provider` does not exist

**Step 3: Create the EDGARProvider skeleton**

Create `engine/src/margin_engine/ingestion/providers/edgar_provider.py`:

```python
"""SEC EDGAR data provider.

Free government API for financial data: XBRL fundamentals, Form 4
insider transactions, and 13F institutional holdings. No API key
required — only a User-Agent header with company name and contact email.

SEC EDGAR docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

logger = logging.getLogger(__name__)

_SEC_DATA_BASE = "https://data.sec.gov"
_SEC_ARCHIVES_BASE = "https://www.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# XBRL tag variants for financial statement fields.
# Each key is the standardized field name; each value is a list of
# XBRL concept tags to try (first match wins).
_INCOME_TAGS: dict[str, list[str]] = {
    "revenue": ["Revenues", "Revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsSold", "CostOfGoodsAndServicesSold"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "eps_basic": ["EarningsPerShareBasic"],
    "eps_diluted": ["EarningsPerShareDiluted"],
}

_BALANCE_TAGS: dict[str, list[str]] = {
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "total_liabilities": ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "stockholders_equity": ["StockholdersEquity"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "long_term_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
}

_CASH_FLOW_TAGS: dict[str, list[str]] = {
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "investing_cash_flow": ["NetCashProvidedByUsedInInvestingActivities"],
    "financing_cash_flow": ["NetCashProvidedByUsedInFinancingActivities"],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditureDiscontinuedOperations",
    ],
}

# Curated list of top institutional investors for 13F lookup.
# Maps fund name -> CIK (zero-padded to 10 digits).
_TOP_FUND_CIKS: dict[str, str] = {
    "Berkshire Hathaway": "0001067983",
    "Baupost Group": "0001061768",
    "Appaloosa Management": "0001656456",
    "Greenlight Capital": "0001079114",
    "Pershing Square": "0001336528",
    "Scion Asset Management": "0001649339",
    "Third Point": "0001040273",
    "Icahn Enterprises": "0000813762",
    "Renaissance Technologies": "0001037389",
    "Bridgewater Associates": "0001350694",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EDGARProvider(DataProvider):
    """Concrete data provider backed by SEC EDGAR.

    Free government API. Supports fundamentals (XBRL), insider
    transactions (Form 4), and institutional holdings (13F).
    Uses per-category priorities: fundamentals at 2 (fallback),
    insider and institutional at 10 (primary above Finnhub).
    """

    def __init__(
        self,
        user_agent: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        if not user_agent:
            raise ValueError("SEC EDGAR requires a User-Agent header")
        self._user_agent = user_agent
        self._rate_limiter = rate_limiter
        self._cik_map: dict[str, int] | None = None
        self._company_names: dict[str, str] | None = None

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="edgar",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.INSIDER,
                DataCategory.INSTITUTIONAL,
            ],
            requests_per_minute=600,
            requires_api_key=False,
            priority=10,
            category_priorities={
                DataCategory.FUNDAMENTALS: 2,
                DataCategory.INSIDER: 10,
                DataCategory.INSTITUTIONAL: 10,
            },
        )

    # ------------------------------------------------------------------
    # CIK mapping
    # ------------------------------------------------------------------

    def _ensure_cik_map(self) -> None:
        """Lazy-load the SEC ticker-to-CIK mapping."""
        if self._cik_map is not None:
            return
        resp = httpx.get(_TICKERS_URL, headers={"User-Agent": self._user_agent})
        resp.raise_for_status()
        data = resp.json()
        self._cik_map = {}
        self._company_names = {}
        for entry in data.values():
            ticker = entry["ticker"].upper()
            self._cik_map[ticker] = entry["cik_str"]
            self._company_names[ticker] = entry["title"]

    def _get_cik(self, ticker: str) -> str:
        """Return zero-padded 10-digit CIK for a ticker."""
        self._ensure_cik_map()
        cik = self._cik_map.get(ticker.upper())
        if cik is None:
            raise ValueError(f"No CIK found for ticker {ticker}")
        return str(cik).zfill(10)

    def _get_company_name(self, ticker: str) -> str:
        """Return company name for a ticker."""
        self._ensure_cik_map()
        return self._company_names.get(ticker.upper(), "")

    # ------------------------------------------------------------------
    # XBRL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_latest_annual(facts: dict, tags: list[str]) -> float | None:
        """Extract the latest 10-K value from company facts for matching tags."""
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        for tag in tags:
            concept = us_gaap.get(tag)
            if concept is None:
                continue
            units = concept.get("units", {})
            values = units.get("USD") or units.get("USD/shares") or []
            annual = [v for v in values if v.get("form") == "10-K"]
            if not annual:
                continue
            annual.sort(key=lambda v: v.get("end", ""), reverse=True)
            return annual[0]["val"]
        return None

    # ------------------------------------------------------------------
    # Fetch methods (stubs — implemented in subsequent tasks)
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch fundamental financial data from XBRL company facts."""
        raise NotImplementedError("fetch_fundamentals not yet implemented")

    def fetch_insider_transactions(self, ticker: str) -> FetchResult:
        """Fetch insider transactions from Form 4 filings."""
        raise NotImplementedError("fetch_insider_transactions not yet implemented")

    def fetch_institutional_holdings(self, ticker: str) -> FetchResult:
        """Fetch institutional holdings from 13F filings."""
        raise NotImplementedError("fetch_institutional_holdings not yet implemented")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/edgar_provider.py engine/tests/ingestion/providers/test_edgar_provider.py
git commit -m "feat(engine): add EDGARProvider skeleton with CIK mapping"
```

---

### Task 3: fetch_fundamentals (XBRL)

Implement the XBRL fundamentals fetch method.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/edgar_provider.py`
- Modify: `engine/tests/ingestion/providers/test_edgar_provider.py`

**Step 1: Write the failing tests**

Add to `test_edgar_provider.py`:

```python
COMPANY_FACTS_RESPONSE = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 383285000000, "form": "10-K", "fy": 2023},
                        {"end": "2022-09-24", "val": 394328000000, "form": "10-K", "fy": 2022},
                        {"end": "2023-07-01", "val": 81797000000, "form": "10-Q", "fy": 2023},
                    ]
                }
            },
            "CostOfRevenue": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 214137000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "GrossProfit": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 169148000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "NetIncomeLoss": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 96995000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "EarningsPerShareBasic": {
                "units": {
                    "USD/shares": [
                        {"end": "2023-09-30", "val": 6.16, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "Assets": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 352755000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "StockholdersEquity": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 62146000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {
                    "USD": [
                        {"end": "2023-09-30", "val": 110543000000, "form": "10-K", "fy": 2023},
                    ]
                }
            },
        }
    },
}


class TestFetchFundamentals:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_success(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.provider_name == "edgar"
        assert result.category == DataCategory.FUNDAMENTALS
        assert result.ticker == "AAPL"
        assert result.raw_data["income_statement"]["revenue"] == 383285000000
        assert result.raw_data["income_statement"]["net_income"] == 96995000000
        assert result.raw_data["balance_sheet"]["total_assets"] == 352755000000
        assert result.raw_data["cash_flow"]["operating_cash_flow"] == 110543000000

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_picks_latest_10k(self, mock_get):
        """Should pick the most recent 10-K, not 10-Q."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        # Should pick 2023 annual (383B), not 2023 quarterly (81B)
        assert result.raw_data["income_statement"]["revenue"] == 383285000000

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_usd_per_shares_unit(self, mock_get):
        """EPS uses USD/shares unit, not plain USD."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=COMPANY_FACTS_RESPONSE),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.raw_data["income_statement"]["eps_basic"] == 6.16

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_missing_tags_omitted(self, mock_get):
        """Fields with no matching XBRL tags are simply absent from raw_data."""
        sparse_facts = {"facts": {"us-gaap": {}}}
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=sparse_facts),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.raw_data["income_statement"] == {}
        assert result.raw_data["balance_sheet"] == {}
        assert result.raw_data["cash_flow"] == {}

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(success=False),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_fundamentals("AAPL")

        assert result.success is False
        assert result.error is not None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py::TestFetchFundamentals -v`
Expected: FAIL — NotImplementedError

**Step 3: Implement fetch_fundamentals**

Replace the stub in `edgar_provider.py`:

```python
    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch fundamental financial data from XBRL company facts.

        Hits the SEC EDGAR companyfacts endpoint and extracts the latest
        10-K annual values for income statement, balance sheet, and cash
        flow fields.
        """
        self._acquire_rate_limit()
        try:
            cik = self._get_cik(ticker)
            url = f"{_SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
            resp = httpx.get(url, headers={"User-Agent": self._user_agent})
            resp.raise_for_status()
            facts = resp.json()

            income: dict[str, float] = {}
            for field, tags in _INCOME_TAGS.items():
                val = self._extract_latest_annual(facts, tags)
                if val is not None:
                    income[field] = val

            balance: dict[str, float] = {}
            for field, tags in _BALANCE_TAGS.items():
                val = self._extract_latest_annual(facts, tags)
                if val is not None:
                    balance[field] = val

            cash_flow: dict[str, float] = {}
            for field, tags in _CASH_FLOW_TAGS.items():
                val = self._extract_latest_annual(facts, tags)
                if val is not None:
                    cash_flow[field] = val

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={
                    "income_statement": income,
                    "balance_sheet": balance,
                    "cash_flow": cash_flow,
                },
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/edgar_provider.py engine/tests/ingestion/providers/test_edgar_provider.py
git commit -m "feat(engine): implement EDGAR fetch_fundamentals (XBRL)"
```

---

### Task 4: fetch_insider_transactions (Form 4)

Implement insider transaction fetching with Form 4 XML parsing.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/edgar_provider.py`
- Modify: `engine/tests/ingestion/providers/test_edgar_provider.py`

**Step 1: Write the failing tests**

Add to `test_edgar_provider.py`:

```python
SUBMISSIONS_RESPONSE = {
    "cik": "320193",
    "entityType": "operating",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-24-000006",
                "0000320193-24-000005",
                "0000320193-24-000004",
            ],
            "filingDate": ["2024-01-26", "2024-01-20", "2024-01-15"],
            "reportDate": ["2024-01-26", "2024-01-20", "2024-01-15"],
            "form": ["4", "10-K", "4"],
            "primaryDocument": ["xslF345X05.xml", "aapl-20231230.htm", "xslF345X05.xml"],
        }
    },
}

FORM4_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001767094</rptOwnerCik>
      <rptOwnerName>COOK TIMOTHY D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>true</isDirector>
      <isOfficer>true</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-01-25</value></transactionDate>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>50000</value></transactionShares>
        <transactionPricePerShare><value>195.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


class TestFetchInsiderTransactions:
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_success(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),       # CIK map
            _make_response(json_data=SUBMISSIONS_RESPONSE),    # submissions
            _make_response(text_data=FORM4_XML),               # Form 4 filing 1
            _make_response(text_data=FORM4_XML),               # Form 4 filing 2
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.provider_name == "edgar"
        assert result.category == DataCategory.INSIDER
        txns = result.raw_data["transactions"]
        assert len(txns) == 2  # Two Form 4 filings, one transaction each
        assert txns[0]["owner_name"] == "COOK TIMOTHY D"
        assert txns[0]["transaction_code"] == "S"
        assert txns[0]["shares"] == 50000.0
        assert txns[0]["price_per_share"] == 195.50
        assert txns[0]["is_officer"] is True
        assert txns[0]["officer_title"] == "Chief Executive Officer"

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_no_form4_filings(self, mock_get):
        no_form4 = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-24-000005"],
                    "filingDate": ["2024-01-20"],
                    "form": ["10-K"],
                    "primaryDocument": ["doc.htm"],
                }
            }
        }
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=no_form4),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert result.raw_data["transactions"] == []

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_xml_parse_error_skipped(self, mock_get):
        """If one filing has bad XML, it's skipped gracefully."""
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=SUBMISSIONS_RESPONSE),
            _make_response(text_data="<not valid xml"),         # bad XML
            _make_response(text_data=FORM4_XML),                # good XML
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is True
        assert len(result.raw_data["transactions"]) == 1

    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = Exception("network timeout")

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_insider_transactions("AAPL")

        assert result.success is False
        assert "network timeout" in result.error
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py::TestFetchInsiderTransactions -v`
Expected: FAIL — NotImplementedError

**Step 3: Implement fetch_insider_transactions and _parse_form4_xml**

Replace the stub in `edgar_provider.py`:

```python
    # ------------------------------------------------------------------
    # Form 4 (insider transactions)
    # ------------------------------------------------------------------

    def fetch_insider_transactions(self, ticker: str) -> FetchResult:
        """Fetch insider transactions from recent Form 4 filings.

        Gets the company's filing history, finds the most recent Form 4
        filings (up to 10), fetches each XML document, and parses
        transaction details.
        """
        self._acquire_rate_limit()
        try:
            cik = self._get_cik(ticker)
            cik_int = str(int(cik))

            url = f"{_SEC_DATA_BASE}/submissions/CIK{cik}.json"
            resp = httpx.get(url, headers={"User-Agent": self._user_agent})
            resp.raise_for_status()
            submissions = resp.json()

            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            dates = recent.get("filingDate", [])
            docs = recent.get("primaryDocument", [])

            form4_indices = [i for i, f in enumerate(forms) if f == "4"][:10]

            transactions: list[dict] = []
            for idx in form4_indices:
                accession_no_dashes = accessions[idx].replace("-", "")
                filing_url = (
                    f"{_SEC_ARCHIVES_BASE}/Archives/edgar/data/{cik_int}/"
                    f"{accession_no_dashes}/{docs[idx]}"
                )

                self._acquire_rate_limit()
                try:
                    filing_resp = httpx.get(
                        filing_url, headers={"User-Agent": self._user_agent}
                    )
                    if not filing_resp.is_success:
                        continue
                    parsed = self._parse_form4_xml(filing_resp.text, dates[idx])
                    transactions.extend(parsed)
                except Exception:
                    logger.debug("Failed to parse Form 4 at %s", filing_url, exc_info=True)
                    continue

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSIDER,
                ticker=ticker,
                raw_data={"transactions": transactions},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSIDER,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _parse_form4_xml(xml_text: str, filing_date: str) -> list[dict]:
        """Parse a Form 4 XML document into transaction dicts."""
        root = ET.fromstring(xml_text)

        owner = root.find(".//reportingOwner")
        owner_name = ""
        owner_cik = ""
        is_director = False
        is_officer = False
        officer_title = ""

        if owner is not None:
            name_el = owner.find(".//rptOwnerName")
            if name_el is not None and name_el.text:
                owner_name = name_el.text
            cik_el = owner.find(".//rptOwnerCik")
            if cik_el is not None and cik_el.text:
                owner_cik = cik_el.text

            rel = owner.find(".//reportingOwnerRelationship")
            if rel is not None:
                dir_el = rel.find("isDirector")
                if dir_el is not None and dir_el.text:
                    is_director = dir_el.text.lower() in ("true", "1")
                off_el = rel.find("isOfficer")
                if off_el is not None and off_el.text:
                    is_officer = off_el.text.lower() in ("true", "1")
                title_el = rel.find("officerTitle")
                if title_el is not None and title_el.text:
                    officer_title = title_el.text

        transactions: list[dict] = []
        for txn in root.findall(".//nonDerivativeTransaction"):
            date_el = txn.find(".//transactionDate/value")
            code_el = txn.find(".//transactionCoding/transactionCode")
            shares_el = txn.find(".//transactionAmounts/transactionShares/value")
            price_el = txn.find(".//transactionAmounts/transactionPricePerShare/value")
            ad_el = txn.find(".//transactionAmounts/transactionAcquiredDisposedCode/value")

            transactions.append({
                "owner_name": owner_name,
                "owner_cik": owner_cik,
                "is_director": is_director,
                "is_officer": is_officer,
                "officer_title": officer_title,
                "transaction_date": date_el.text if date_el is not None and date_el.text else "",
                "transaction_code": code_el.text if code_el is not None and code_el.text else "",
                "shares": float(shares_el.text) if shares_el is not None and shares_el.text else 0.0,
                "price_per_share": (
                    float(price_el.text) if price_el is not None and price_el.text else 0.0
                ),
                "acquired_disposed": ad_el.text if ad_el is not None and ad_el.text else "",
                "filing_date": filing_date,
            })

        return transactions
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/edgar_provider.py engine/tests/ingestion/providers/test_edgar_provider.py
git commit -m "feat(engine): implement EDGAR fetch_insider_transactions (Form 4)"
```

---

### Task 5: fetch_institutional_holdings (13F)

Implement institutional holdings fetching with 13F XML parsing.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/edgar_provider.py`
- Modify: `engine/tests/ingestion/providers/test_edgar_provider.py`

**Step 1: Write the failing tests**

Add to `test_edgar_provider.py`:

```python
FUND_SUBMISSIONS_RESPONSE = {
    "cik": "1067983",
    "name": "BERKSHIRE HATHAWAY INC",
    "filings": {
        "recent": {
            "accessionNumber": ["0001067983-24-000010", "0001067983-24-000005"],
            "filingDate": ["2024-11-14", "2024-08-14"],
            "reportDate": ["2024-09-30", "2024-06-30"],
            "form": ["13F-HR", "13F-HR"],
            "primaryDocument": ["primary.htm", "primary.htm"],
        }
    },
}

FILING_INDEX_RESPONSE = {
    "directory": {
        "item": [
            {"name": "primary.htm", "type": "primary_doc"},
            {"name": "infotable.xml", "type": "informationtable"},
            {"name": "primary_doc.xml", "type": "xml"},
        ]
    }
}

INFOTABLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>45123</value>
    <shrsOrPrnAmt>
      <sshPrnamt>250000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>250000</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>MICROSOFT CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>594918104</cusip>
    <value>30000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>100000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>100000</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
</informationTable>
"""


class TestFetchInstitutionalHoldings:
    @patch(
        "margin_engine.ingestion.providers.edgar_provider._TOP_FUND_CIKS",
        {"Berkshire Hathaway": "0001067983"},
    )
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_success(self, mock_get):
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),           # CIK map
            _make_response(json_data=FUND_SUBMISSIONS_RESPONSE),   # fund submissions
            _make_response(json_data=FILING_INDEX_RESPONSE),       # filing index
            _make_response(text_data=INFOTABLE_XML),               # infotable
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.provider_name == "edgar"
        assert result.category == DataCategory.INSTITUTIONAL
        holdings = result.raw_data["holdings"]
        assert len(holdings) == 1
        assert holdings[0]["fund_name"] == "BERKSHIRE HATHAWAY INC"
        assert holdings[0]["shares"] == 250000
        assert holdings[0]["value_thousands"] == 45123

    @patch(
        "margin_engine.ingestion.providers.edgar_provider._TOP_FUND_CIKS",
        {"Berkshire Hathaway": "0001067983"},
    )
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_no_matching_holdings(self, mock_get):
        """Fund holds other stocks but not the target ticker."""
        no_apple_xml = INFOTABLE_XML.replace("APPLE INC", "COCA COLA CO")
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=FUND_SUBMISSIONS_RESPONSE),
            _make_response(json_data=FILING_INDEX_RESPONSE),
            _make_response(text_data=no_apple_xml),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.raw_data["holdings"] == []

    @patch(
        "margin_engine.ingestion.providers.edgar_provider._TOP_FUND_CIKS",
        {"Berkshire Hathaway": "0001067983"},
    )
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_fund_with_no_13f_skipped(self, mock_get):
        """Fund with no 13F filings is skipped gracefully."""
        no_13f = {
            "filings": {
                "recent": {
                    "accessionNumber": [],
                    "filingDate": [],
                    "reportDate": [],
                    "form": [],
                    "primaryDocument": [],
                }
            }
        }
        mock_get.side_effect = [
            _make_response(json_data=CIK_MAP_RESPONSE),
            _make_response(json_data=no_13f),
        ]

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is True
        assert result.raw_data["holdings"] == []

    @patch(
        "margin_engine.ingestion.providers.edgar_provider._TOP_FUND_CIKS",
        {"Berkshire Hathaway": "0001067983"},
    )
    @patch("margin_engine.ingestion.providers.edgar_provider.httpx.get")
    def test_api_error(self, mock_get):
        mock_get.side_effect = Exception("connection refused")

        provider = EDGARProvider(user_agent="Test test@example.com")
        result = provider.fetch_institutional_holdings("AAPL")

        assert result.success is False
        assert "connection refused" in result.error
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py::TestFetchInstitutionalHoldings -v`
Expected: FAIL — NotImplementedError

**Step 3: Implement fetch_institutional_holdings and helpers**

Replace the stub in `edgar_provider.py`:

```python
    # ------------------------------------------------------------------
    # 13F (institutional holdings)
    # ------------------------------------------------------------------

    def fetch_institutional_holdings(self, ticker: str) -> FetchResult:
        """Fetch institutional holdings from curated funds' 13F filings.

        Checks a curated list of top institutional investors' most
        recent 13F-HR filings for holdings matching the target company.
        """
        self._acquire_rate_limit()
        try:
            company_name = self._get_company_name(ticker)
            if not company_name:
                raise ValueError(f"No company name found for {ticker}")

            holdings: list[dict] = []

            for fund_name_label, fund_cik in _TOP_FUND_CIKS.items():
                try:
                    self._acquire_rate_limit()
                    fund_holdings = self._fetch_fund_13f(fund_cik, company_name)
                    holdings.extend(fund_holdings)
                except Exception:
                    logger.debug(
                        "Failed to fetch 13F for %s (%s)",
                        fund_name_label,
                        fund_cik,
                        exc_info=True,
                    )
                    continue

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSTITUTIONAL,
                ticker=ticker,
                raw_data={"holdings": holdings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.INSTITUTIONAL,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    def _fetch_fund_13f(self, fund_cik: str, target_company: str) -> list[dict]:
        """Fetch a single fund's latest 13F and filter for target company."""
        cik_int = str(int(fund_cik))

        url = f"{_SEC_DATA_BASE}/submissions/CIK{fund_cik}.json"
        resp = httpx.get(url, headers={"User-Agent": self._user_agent})
        resp.raise_for_status()
        submissions = resp.json()

        fund_name = submissions.get("name", "")
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])

        # Find the latest 13F-HR
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A"):
                accession_no_dashes = accessions[i].replace("-", "")

                # Find the infotable XML via the filing index
                infotable_url = self._find_13f_infotable(cik_int, accession_no_dashes)
                if infotable_url is None:
                    return []

                self._acquire_rate_limit()
                info_resp = httpx.get(
                    infotable_url, headers={"User-Agent": self._user_agent}
                )
                if not info_resp.is_success:
                    return []

                return self._parse_13f_infotable(
                    info_resp.text,
                    target_company,
                    fund_name,
                    fund_cik,
                    filing_dates[i] if i < len(filing_dates) else "",
                    report_dates[i] if i < len(report_dates) else "",
                )

        return []

    def _find_13f_infotable(self, cik_int: str, accession_no_dashes: str) -> str | None:
        """Find the infotable XML URL for a 13F filing via its index."""
        self._acquire_rate_limit()
        index_url = (
            f"{_SEC_ARCHIVES_BASE}/Archives/edgar/data/{cik_int}/"
            f"{accession_no_dashes}/index.json"
        )
        resp = httpx.get(index_url, headers={"User-Agent": self._user_agent})
        if not resp.is_success:
            return None

        index = resp.json()
        for doc in index.get("directory", {}).get("item", []):
            name = doc.get("name", "").lower()
            if "infotable" in name and name.endswith(".xml"):
                return (
                    f"{_SEC_ARCHIVES_BASE}/Archives/edgar/data/{cik_int}/"
                    f"{accession_no_dashes}/{doc['name']}"
                )
        return None

    @staticmethod
    def _parse_13f_infotable(
        xml_text: str,
        target_company: str,
        fund_name: str,
        fund_cik: str,
        filing_date: str,
        report_date: str,
    ) -> list[dict]:
        """Parse 13F infotable XML, filtering for a target company."""
        # Strip namespace for simpler parsing
        cleaned = re.sub(r'\sxmlns="[^"]*"', "", xml_text, count=1)
        root = ET.fromstring(cleaned)

        target_upper = target_company.upper()
        holdings: list[dict] = []

        for entry in root.findall(".//infoTable"):
            issuer = (entry.findtext("nameOfIssuer") or "").upper()
            if target_upper not in issuer and issuer not in target_upper:
                continue

            shares_el = entry.find("shrsOrPrnAmt/sshPrnamt")
            value_text = entry.findtext("value") or "0"
            cusip = entry.findtext("cusip") or ""

            holdings.append({
                "fund_name": fund_name,
                "fund_cik": fund_cik,
                "issuer_name": issuer,
                "cusip": cusip,
                "shares": int(shares_el.text) if shares_el is not None and shares_el.text else 0,
                "value_thousands": int(value_text) if value_text else 0,
                "filing_date": filing_date,
                "report_date": report_date,
            })

        return holdings
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/providers/test_edgar_provider.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/edgar_provider.py engine/tests/ingestion/providers/test_edgar_provider.py
git commit -m "feat(engine): implement EDGAR fetch_institutional_holdings (13F)"
```

---

### Task 6: Package Exports + API Config

Export `EDGARProvider` from package `__init__.py` files and add `edgar_user_agent` to API config.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/__init__.py`
- Modify: `engine/src/margin_engine/ingestion/__init__.py`
- Modify: `api/src/margin_api/config.py`

**Step 1: Update providers/__init__.py**

Add `EDGARProvider` to `engine/src/margin_engine/ingestion/providers/__init__.py`:

```python
"""Concrete data provider implementations."""

from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider
from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

__all__ = ["EDGARProvider", "FinnhubProvider", "FMPProvider", "PolygonProvider", "YFinanceProvider"]
```

**Step 2: Update ingestion/__init__.py**

Add `EDGARProvider` to the top-level exports in `engine/src/margin_engine/ingestion/__init__.py`. Add the import and add `"EDGARProvider"` to the `__all__` list (alphabetically).

**Step 3: Add edgar_user_agent to API config**

In `api/src/margin_api/config.py`, add to the Data providers section:

```python
    # Data providers
    polygon_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
    edgar_user_agent: str = ""
```

**Step 4: Run existing tests to verify nothing broke**

Run: `uv run pytest engine/tests/ api/tests/ -v --timeout=60`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/__init__.py engine/src/margin_engine/ingestion/__init__.py api/src/margin_api/config.py
git commit -m "feat: export EDGARProvider and add edgar_user_agent config"
```

---

### Task 7: Registry Integration Tests

Test that EDGARProvider integrates correctly with the registry, especially per-category priority behavior.

**Files:**
- Modify: `engine/tests/ingestion/test_registry.py`

**Step 1: Write the tests**

Add a new test class at the bottom of `engine/tests/ingestion/test_registry.py`:

```python
# ---------------------------------------------------------------------------
# Tests: real EDGARProvider in fallback chain
# ---------------------------------------------------------------------------


class TestEdgarInFallbackChain:
    """Verify real EDGARProvider integrates with registry per-category priority."""

    def test_edgar_is_last_for_fundamentals(self):
        from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry()
        registry.register(YFinanceProvider())
        registry.register(EDGARProvider(user_agent="Test test@example.com"))

        chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        names = [p.info.name for p in chain]
        assert names == ["yfinance", "edgar"]

    def test_edgar_above_finnhub_for_insider(self):
        from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))
        registry.register(EDGARProvider(user_agent="Test test@example.com"))

        chain = registry.get_fallback_chain(DataCategory.INSIDER)
        names = [p.info.name for p in chain]
        assert names == ["edgar", "finnhub"]

    def test_edgar_above_finnhub_for_institutional(self):
        from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
        from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider

        registry = ProviderRegistry(api_keys={"finnhub": "test_key"})
        registry.register(FinnhubProvider(api_key="test_key"))
        registry.register(EDGARProvider(user_agent="Test test@example.com"))

        chain = registry.get_fallback_chain(DataCategory.INSTITUTIONAL)
        names = [p.info.name for p in chain]
        assert names == ["edgar", "finnhub"]

    def test_edgar_not_in_price_chain(self):
        from margin_engine.ingestion.providers.edgar_provider import EDGARProvider

        registry = ProviderRegistry()
        registry.register(EDGARProvider(user_agent="Test test@example.com"))

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 0

    def test_full_fundamentals_chain(self):
        from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry(api_keys={"fmp": "test_key"})
        registry.register(YFinanceProvider())
        registry.register(FMPProvider(api_key="test_key"))
        registry.register(EDGARProvider(user_agent="Test test@example.com"))

        chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        names = [p.info.name for p in chain]
        assert names == ["yfinance", "fmp", "edgar"]
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_registry.py::TestEdgarInFallbackChain -v`
Expected: ALL PASS

**Step 3: Run the full test suite**

Run: `uv run pytest engine/tests/ingestion/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add engine/tests/ingestion/test_registry.py
git commit -m "test(engine): add EDGAR registry integration tests"
```

---

### Task 8: Lint, Format, and Full Suite Verification

Verify the entire codebase passes lint and all tests.

**Step 1: Run ruff format check**

Run: `uv run ruff format --check engine/ api/`
If failures: `uv run ruff format engine/ api/`

**Step 2: Run ruff lint check**

Run: `uv run ruff check engine/ api/`
If failures: `uv run ruff check --fix engine/ api/`

**Step 3: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 4: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: ALL PASS

**Step 5: Commit any format/lint fixes**

```bash
git add -u && git commit -m "style: fix lint and formatting issues"
```
