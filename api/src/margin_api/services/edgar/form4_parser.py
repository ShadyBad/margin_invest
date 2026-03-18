"""SEC Form 4 XML parser for insider transaction data.

Extracts open-market purchase transactions (transactionCode == 'P') from
SEC Form 4 XML filings. Uses Python's stdlib xml.etree.ElementTree -- no
external XML library needed.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from margin_engine.models.financial import InsiderTransaction

logger = logging.getLogger(__name__)


def _text(el: ElementTree.Element | None, path: str) -> str:
    """Safely extract text from an XML path, returning empty string if missing."""
    if el is None:
        return ""
    node = el.find(path)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _value_text(el: ElementTree.Element | None, path: str) -> str:
    """Extract text from a <path><value>TEXT</value></path> pattern."""
    if el is None:
        return ""
    container = el.find(path)
    if container is None:
        return ""
    value_el = container.find("value")
    if value_el is None or value_el.text is None:
        return ""
    return value_el.text.strip()


class Form4Parser:
    """Parse SEC Form 4 XML and extract purchase transactions."""

    def parse(self, form4_xml: str) -> list[InsiderTransaction]:
        """Extract purchase transactions from Form 4 XML.

        Args:
            form4_xml: Raw XML string of a Form 4 filing.

        Returns:
            List of InsiderTransaction for each open-market purchase (code 'P').
            Returns empty list for malformed XML, empty filings, or filings
            with no purchase transactions.
        """
        if not form4_xml or not form4_xml.strip():
            return []

        try:
            root = ElementTree.fromstring(form4_xml)  # noqa: S314
        except ElementTree.ParseError:
            logger.warning("Failed to parse Form 4 XML")
            return []

        # Extract issuer metadata (for logging; not stored on InsiderTransaction)
        issuer = root.find("issuer")
        issuer_ticker = _text(issuer, "issuerTradingSymbol")
        issuer_cik = _text(issuer, "issuerCik")

        # Extract first reporting owner
        owner = root.find("reportingOwner")
        if owner is None:
            logger.warning("Form 4 XML has no reportingOwner element")
            return []

        owner_id = owner.find("reportingOwnerId")
        insider_cik = _text(owner_id, "rptOwnerCik")
        insider_name = _text(owner_id, "rptOwnerName")

        # Determine title from relationship
        relationship = owner.find("reportingOwnerRelationship")
        title = self._extract_title(relationship)

        # Find non-derivative transactions
        nd_table = root.find("nonDerivativeTable")
        if nd_table is None:
            return []

        transactions: list[InsiderTransaction] = []
        for txn_el in nd_table.findall("nonDerivativeTransaction"):
            code = _text(txn_el, "transactionCoding/transactionCode")
            if code != "P":
                continue

            txn_date = _value_text(txn_el, "transactionDate")
            amounts = txn_el.find("transactionAmounts")
            shares_str = _value_text(amounts, "transactionShares") if amounts is not None else ""
            price_str = (
                _value_text(amounts, "transactionPricePerShare") if amounts is not None else ""
            )

            shares = self._parse_int(shares_str)
            price = self._parse_decimal(price_str)
            value = price * shares

            transactions.append(
                InsiderTransaction(
                    date=txn_date,
                    insider_name=insider_name,
                    insider_cik=insider_cik,
                    title=title,
                    transaction_type="buy",
                    shares=shares,
                    price_per_share=price,
                    value=value,
                )
            )

        if transactions:
            logger.info(
                "Parsed %d purchase(s) from Form 4: %s (CIK %s), insider %s",
                len(transactions),
                issuer_ticker,
                issuer_cik,
                insider_name,
            )

        return transactions

    @staticmethod
    def _extract_title(relationship: ElementTree.Element | None) -> str:
        """Determine insider title from reportingOwnerRelationship element."""
        if relationship is None:
            return "Unknown"

        # Officer title takes priority
        officer_title = _text(relationship, "officerTitle")
        if officer_title:
            return officer_title

        # Fall back to role flags
        if _text(relationship, "isDirector") == "1":
            return "Director"
        if _text(relationship, "isTenPercentOwner") == "1":
            return "10% Owner"
        if _text(relationship, "isOther") == "1":
            other_text = _text(relationship, "otherText")
            return other_text or "Other"

        return "Unknown"

    @staticmethod
    def _parse_int(s: str) -> int:
        """Parse string to int, returning 0 on failure."""
        if not s:
            return 0
        try:
            return int(Decimal(s))
        except (ValueError, InvalidOperation):
            return 0

    @staticmethod
    def _parse_decimal(s: str) -> Decimal:
        """Parse string to Decimal, returning Decimal('0') on failure."""
        if not s:
            return Decimal("0")
        try:
            return Decimal(s)
        except InvalidOperation:
            return Decimal("0")
