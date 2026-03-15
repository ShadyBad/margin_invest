"""XBRL parser for extracting financial data from US-GAAP tagged filings."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from lxml import etree

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# US-GAAP tag mapping: our field name -> ordered list of GAAP local names
# Primary tag first, fallbacks after.
# ---------------------------------------------------------------------------

GAAP_TAG_MAP: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfRevenue",
    ],
    "gross_profit": ["GrossProfit"],
    "sga_expense": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "ebit": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ],
    "interest_expense": ["InterestExpense", "InterestExpenseDebt"],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "total_assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "total_liabilities": ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "short_term_debt": ["ShortTermBorrowings", "DebtCurrent"],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "operating_cash_flow": [
        "NetCashProvidedByOperatingActivities",
        "CashFlowsFromOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PurchaseOfPropertyPlantAndEquipment",
    ],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "share_repurchases": ["PaymentsForRepurchaseOfCommonStock"],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesIssued",
    ],
    "pp_and_e": ["PropertyPlantAndEquipmentNet"],
    "depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
    ],
    "tax_provision": ["IncomeTaxExpenseBenefit"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
}

# ---------------------------------------------------------------------------
# Field classification sets
# ---------------------------------------------------------------------------

_INCOME_FIELDS: set[str] = {
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "sga_expense",
    "rd_expense",
    "ebit",
    "interest_expense",
    "net_income",
    "depreciation",
    "tax_provision",
}

_BALANCE_FIELDS: set[str] = {
    "total_assets",
    "current_assets",
    "cash_and_equivalents",
    "total_liabilities",
    "current_liabilities",
    "long_term_debt",
    "short_term_debt",
    "total_equity",
    "retained_earnings",
    "pp_and_e",
    "receivables",
}

_CASHFLOW_FIELDS: set[str] = {
    "operating_cash_flow",
    "capex",
    "dividends_paid",
    "share_repurchases",
}

# Regex to match any US-GAAP taxonomy namespace (varies by year).
# Pre-2012 filings use xbrl.us domain (e.g. http://xbrl.us/us-gaap/2009-01-31),
# 2012+ filings use fasb.org (e.g. /2013-01-31 or /2024).
_GAAP_NS_RE = re.compile(r"^http://(fasb\.org|xbrl\.us)/us-gaap/\d{4}(-\d{2}-\d{2})?$")

# Regex to match SEC DEI (Document & Entity Information) namespace.
# Pre-2012: xbrl.us/dei, 2012+: xbrl.sec.gov/dei.
_DEI_NS_RE = re.compile(r"^http://(xbrl\.sec\.gov|xbrl\.us)/dei(-\w+)?/\d{4}(-\d{2}-\d{2})?$")

# DEI-namespace tag mapping. Tags here are checked when no GAAP tag matched.
# Priority values are offset by 100 so GAAP tags always win.
DEI_TAG_MAP: dict[str, list[str]] = {
    "shares_outstanding": [
        "EntityCommonStockSharesOutstanding",
    ],
}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class XBRLFinancials:
    """Parsed financial data from an XBRL instance document."""

    income_statement: dict[str, float | None] = field(default_factory=dict)
    balance_sheet: dict[str, float | None] = field(default_factory=dict)
    cash_flow: dict[str, float | None] = field(default_factory=dict)
    shares_outstanding: int | None = None


# ---------------------------------------------------------------------------
# Reverse lookup: GAAP local name -> (our_field_name, priority)
# Lower priority number = preferred tag.
# ---------------------------------------------------------------------------


def _build_reverse_map() -> dict[str, tuple[str, int]]:
    """Build a reverse lookup from tag local name to (field_name, priority).

    GAAP tags get priorities 0..N, DEI tags get priorities 100..100+N so
    GAAP tags always win when both namespaces contain the same field.
    """
    reverse: dict[str, tuple[str, int]] = {}
    for field_name, tags in GAAP_TAG_MAP.items():
        for priority, tag in enumerate(tags):
            if tag not in reverse:
                reverse[tag] = (field_name, priority)
    for field_name, tags in DEI_TAG_MAP.items():
        for priority, tag in enumerate(tags):
            if tag not in reverse:
                reverse[tag] = (field_name, 100 + priority)
    return reverse


_REVERSE_MAP = _build_reverse_map()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_financials(xbrl_content: str) -> XBRLFinancials:
    """Parse an XBRL instance document and extract financial data.

    Args:
        xbrl_content: Raw XML string of an XBRL instance document.

    Returns:
        XBRLFinancials with populated income_statement, balance_sheet,
        cash_flow dicts and shares_outstanding.
    """
    if not xbrl_content or not xbrl_content.strip():
        return XBRLFinancials()

    try:
        root = etree.fromstring(xbrl_content.encode("utf-8"))
    except etree.XMLSyntaxError:
        logger.warning("Failed to parse XBRL content as XML")
        return XBRLFinancials()

    # Collect values: field_name -> (priority, raw_value_str)
    # First occurrence of a tag wins (per the spec: "First occurrence wins").
    # Among different tags mapping to the same field, lower priority wins.
    best: dict[str, tuple[int, str]] = {}
    seen_tags: set[str] = set()

    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        ns = _namespace(elem.tag)
        local = _localname(elem.tag)

        # Only consider US-GAAP and DEI namespace elements
        if ns is None or not (_GAAP_NS_RE.match(ns) or _DEI_NS_RE.match(ns)):
            continue

        # First occurrence of each tag wins
        if local in seen_tags:
            continue
        seen_tags.add(local)

        # Check if this tag maps to one of our fields
        mapping = _REVERSE_MAP.get(local)
        if mapping is None:
            continue

        field_name, priority = mapping
        text = (elem.text or "").strip()
        if not text:
            continue

        # Keep the tag with the lowest priority (most preferred)
        existing = best.get(field_name)
        if existing is None or priority < existing[0]:
            best[field_name] = (priority, text)

    # Build result
    result = XBRLFinancials()

    for field_name, (_priority, raw_value) in best.items():
        if field_name == "shares_outstanding":
            try:
                result.shares_outstanding = int(float(raw_value))
            except (ValueError, OverflowError):
                logger.warning("Could not parse shares_outstanding: %s", raw_value)
            continue

        # Parse as float
        try:
            value = float(raw_value)
        except (ValueError, OverflowError):
            logger.warning("Could not parse %s value: %s", field_name, raw_value)
            continue

        # Classify into statement
        if field_name in _INCOME_FIELDS:
            result.income_statement[field_name] = value
        elif field_name in _BALANCE_FIELDS:
            result.balance_sheet[field_name] = value
        elif field_name in _CASHFLOW_FIELDS:
            result.cash_flow[field_name] = value

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _namespace(tag: str) -> str | None:
    """Extract namespace URI from a Clark-notation tag like '{ns}local'."""
    if tag.startswith("{"):
        return tag[1 : tag.index("}")]
    return None


def _localname(tag: str) -> str:
    """Extract local name from a Clark-notation tag like '{ns}local'."""
    if "}" in tag:
        return tag[tag.index("}") + 1 :]
    return tag
