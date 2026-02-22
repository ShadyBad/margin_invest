"""SEC EDGAR data provider.

Free government API for financial data: XBRL fundamentals, Form 4
insider transactions, and 13F institutional holdings. No API key
required -- only a User-Agent header with company name and contact email.

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
    # Fetch methods (stubs -- implemented in subsequent tasks)
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
