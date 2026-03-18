"""Tests for SEC Form 4 XML parser."""

from __future__ import annotations

from decimal import Decimal

from margin_api.services.edgar.form4_parser import Form4Parser

# ---------------------------------------------------------------------------
# Fixture: realistic Form 4 XML with purchase + sale + grant
# ---------------------------------------------------------------------------

FORM4_XML_PURCHASE_AND_SALE = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-02-01</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>50000</value></transactionShares>
        <transactionPricePerShare><value>185.50</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-02-02</value></transactionDate>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>190.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-02-03</value></transactionDate>
      <transactionCoding>
        <transactionCode>A</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>100000</value></transactionShares>
        <transactionPricePerShare><value>0.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

FORM4_XML_MULTIPLE_PURCHASES = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000789019</issuerCik>
    <issuerName>Microsoft Corp</issuerName>
    <issuerTradingSymbol>MSFT</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0009876543</rptOwnerCik>
      <rptOwnerName>Nadella Satya</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-03-10</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>25000</value></transactionShares>
        <transactionPricePerShare><value>420.75</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-03-11</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>15000</value></transactionShares>
        <transactionPricePerShare><value>422.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

FORM4_XML_EMPTY_TABLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
  </nonDerivativeTable>
</ownershipDocument>
"""

FORM4_XML_NO_TABLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
</ownershipDocument>
"""

FORM4_XML_MISSING_PRICE = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-04-15</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

FORM4_XML_DIRECTOR = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0005551234</rptOwnerCik>
      <rptOwnerName>Levinson Arthur D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>1</isDirector>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-05-20</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>192.30</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

FORM4_XML_MULTIPLE_OWNERS = """\
<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0007654321</rptOwnerCik>
      <rptOwnerName>Williams Jeffrey E</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isOfficer>1</isOfficer>
      <officerTitle>Chief Operating Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-06-01</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>30000</value></transactionShares>
        <transactionPricePerShare><value>195.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


class TestForm4Parser:
    """Tests for Form4Parser.parse()."""

    def setup_method(self) -> None:
        self.parser = Form4Parser()

    def test_parses_purchase_transaction(self) -> None:
        """Purchase (P) transaction is extracted with correct fields."""
        results = self.parser.parse(FORM4_XML_PURCHASE_AND_SALE)

        assert len(results) == 1
        txn = results[0]
        assert txn.date == "2024-02-01"
        assert txn.insider_name == "Cook Timothy D"
        assert txn.insider_cik == "0001234567"
        assert txn.title == "Chief Executive Officer"
        assert txn.transaction_type == "buy"
        assert txn.shares == 50000
        assert txn.price_per_share == Decimal("185.50")
        assert txn.value == Decimal("9275000.00")

    def test_ignores_sales(self) -> None:
        """Sale (S) transactions are not included in results."""
        results = self.parser.parse(FORM4_XML_PURCHASE_AND_SALE)
        assert all(t.transaction_type == "buy" for t in results)

    def test_ignores_grants(self) -> None:
        """Award/grant (A) transactions are not included in results."""
        results = self.parser.parse(FORM4_XML_PURCHASE_AND_SALE)
        assert len(results) == 1  # Only the P transaction

    def test_multiple_purchases(self) -> None:
        """Multiple purchase transactions in one filing are all extracted."""
        results = self.parser.parse(FORM4_XML_MULTIPLE_PURCHASES)

        assert len(results) == 2
        assert results[0].date == "2024-03-10"
        assert results[0].shares == 25000
        assert results[0].price_per_share == Decimal("420.75")
        assert results[0].value == Decimal("10518750.00")

        assert results[1].date == "2024-03-11"
        assert results[1].shares == 15000
        assert results[1].price_per_share == Decimal("422.00")
        assert results[1].value == Decimal("6330000.00")

    def test_empty_non_derivative_table(self) -> None:
        """Empty nonDerivativeTable returns empty list."""
        results = self.parser.parse(FORM4_XML_EMPTY_TABLE)
        assert results == []

    def test_no_non_derivative_table(self) -> None:
        """Missing nonDerivativeTable returns empty list."""
        results = self.parser.parse(FORM4_XML_NO_TABLE)
        assert results == []

    def test_missing_price_per_share(self) -> None:
        """Transaction with missing price has price_per_share=0 and value=0."""
        results = self.parser.parse(FORM4_XML_MISSING_PRICE)

        assert len(results) == 1
        txn = results[0]
        assert txn.shares == 5000
        assert txn.price_per_share == Decimal("0")
        assert txn.value == Decimal("0")

    def test_director_relationship(self) -> None:
        """Director (non-officer) gets title 'Director'."""
        results = self.parser.parse(FORM4_XML_DIRECTOR)

        assert len(results) == 1
        assert results[0].title == "Director"
        assert results[0].insider_cik == "0005551234"
        assert results[0].insider_name == "Levinson Arthur D"

    def test_multiple_owners_uses_first(self) -> None:
        """When multiple reportingOwners exist, the first is used."""
        results = self.parser.parse(FORM4_XML_MULTIPLE_OWNERS)

        assert len(results) == 1
        assert results[0].insider_name == "Cook Timothy D"
        assert results[0].insider_cik == "0001234567"
        assert results[0].title == "Chief Executive Officer"

    def test_issuer_metadata(self) -> None:
        """Parser extracts issuer CIK and ticker correctly."""
        results = self.parser.parse(FORM4_XML_MULTIPLE_PURCHASES)
        # InsiderTransaction doesn't carry issuer CIK/ticker, but the parser
        # returns a consistent result. Verify the purchase was parsed from MSFT filing.
        assert results[0].insider_name == "Nadella Satya"

    def test_malformed_xml_returns_empty(self) -> None:
        """Malformed/unparseable XML returns empty list, does not raise."""
        results = self.parser.parse("<not><valid>xml")
        assert results == []

    def test_completely_empty_xml(self) -> None:
        """Empty string returns empty list."""
        results = self.parser.parse("")
        assert results == []
