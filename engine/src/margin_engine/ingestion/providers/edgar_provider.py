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
                "transaction_date": (
                    date_el.text if date_el is not None and date_el.text else ""
                ),
                "transaction_code": (
                    code_el.text if code_el is not None and code_el.text else ""
                ),
                "shares": (
                    float(shares_el.text) if shares_el is not None and shares_el.text else 0.0
                ),
                "price_per_share": (
                    float(price_el.text) if price_el is not None and price_el.text else 0.0
                ),
                "acquired_disposed": (
                    ad_el.text if ad_el is not None and ad_el.text else ""
                ),
                "filing_date": filing_date,
            })

        return transactions

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
                "shares": (
                    int(shares_el.text) if shares_el is not None and shares_el.text else 0
                ),
                "value_thousands": int(value_text) if value_text else 0,
                "filing_date": filing_date,
                "report_date": report_date,
            })

        return holdings
