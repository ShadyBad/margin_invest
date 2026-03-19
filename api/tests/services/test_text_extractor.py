"""Tests for the FilingTextExtractor service.

Tests follow TDD: written first, then the implementation makes them pass.
"""

from __future__ import annotations

import hashlib

import pytest

from margin_api.services.edgar.text_extractor import ExtractedSections, FilingTextExtractor


@pytest.fixture()
def extractor() -> FilingTextExtractor:
    return FilingTextExtractor()


# ---------------------------------------------------------------------------
# Helpers — minimal HTML fixtures
# ---------------------------------------------------------------------------

_10K_HTML = """
<html><body>
<p><b>Item 1. Business</b></p>
<p>We sell widgets to enterprises globally. Our business model is subscription-based.</p>
<p><b>Item 1A. Risk Factors</b></p>
<p>Risks include competition, regulatory changes, and macroeconomic downturns.</p>
<p><b>Item 2. Properties</b></p>
<p>We lease office space in San Francisco.</p>
<p><b>Item 7. Management's Discussion and Analysis</b></p>
<p>Revenue increased 20% year-over-year driven by new customer acquisition.</p>
<p><b>Item 8. Financial Statements</b></p>
<p>See consolidated financial statements.</p>
</body></html>
"""

_10Q_HTML = """
<html><body>
<p><b>Part I</b></p>
<p><b>Item 2. Management's Discussion and Analysis</b></p>
<p>Quarterly revenue grew 15% sequentially due to strong enterprise demand.</p>
<p><b>Item 3. Quantitative and Qualitative Disclosures</b></p>
<p>Market risk remains moderate.</p>
<p><b>Part II</b></p>
<p><b>Item 1A. Risk Factors</b></p>
<p>See annual report for a full discussion of risk factors.</p>
<p><b>Item 6. Exhibits</b></p>
<p>See exhibit index.</p>
</body></html>
"""

_EMPTY_HTML = ""
_MALFORMED_HTML = "<html><body><p>No recognizable sections here.</p></body></html>"


# ---------------------------------------------------------------------------
# 10-K tests
# ---------------------------------------------------------------------------


class TestExtract10K:
    def test_business_extracted(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        assert result.business is not None
        assert "widgets" in result.business.lower()

    def test_risk_factors_extracted(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        assert result.risk_factors is not None
        assert "competition" in result.risk_factors.lower()

    def test_mda_extracted(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        assert result.mda is not None
        assert "revenue" in result.mda.lower()

    def test_all_three_sections_extracted(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        assert result.business is not None
        assert result.risk_factors is not None
        assert result.mda is not None

    def test_html_tags_stripped(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        # No HTML tags should remain in text
        assert "<p>" not in (result.business or "")
        assert "<b>" not in (result.risk_factors or "")
        assert "</p>" not in (result.mda or "")

    def test_sections_capped_at_50k_chars(self, extractor: FilingTextExtractor) -> None:
        long_text = "word " * 20000  # ~100K chars
        big_html = f"""
        <html><body>
        <p>Item 1. Business</p>
        <p>{long_text}</p>
        <p>Item 1A. Risk Factors</p>
        <p>short</p>
        <p>Item 7. MD&amp;A</p>
        <p>short</p>
        </body></html>
        """
        result = extractor.extract_sections(big_html, "10-K")
        assert result.business is not None
        assert len(result.business) <= 50_000


# ---------------------------------------------------------------------------
# 10-Q tests
# ---------------------------------------------------------------------------


class TestExtract10Q:
    def test_business_is_none_for_10q(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10Q_HTML, "10-Q")
        assert result.business is None

    def test_mda_extracted_from_part_i_item_2(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10Q_HTML, "10-Q")
        assert result.mda is not None
        assert "quarterly revenue" in result.mda.lower()

    def test_risk_factors_extracted_from_part_ii_item_1a(
        self, extractor: FilingTextExtractor
    ) -> None:
        result = extractor.extract_sections(_10Q_HTML, "10-Q")
        assert result.risk_factors is not None
        assert "annual report" in result.risk_factors.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_html_returns_all_none(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_EMPTY_HTML, "10-K")
        assert result.business is None
        assert result.risk_factors is None
        assert result.mda is None

    def test_malformed_html_returns_all_none(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_MALFORMED_HTML, "10-K")
        # May or may not extract sections — just shouldn't raise
        # No section headers present, so all should be None
        assert result.business is None
        assert result.risk_factors is None
        assert result.mda is None

    def test_hash_is_consistent(self, extractor: FilingTextExtractor) -> None:
        result1 = extractor.extract_sections(_10K_HTML, "10-K")
        result2 = extractor.extract_sections(_10K_HTML, "10-K")
        assert result1.html_hash == result2.html_hash

    def test_hash_differs_for_different_input(self, extractor: FilingTextExtractor) -> None:
        result1 = extractor.extract_sections(_10K_HTML, "10-K")
        result2 = extractor.extract_sections(_10Q_HTML, "10-Q")
        assert result1.html_hash != result2.html_hash

    def test_hash_is_sha256_hex(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        expected = hashlib.sha256(_10K_HTML.encode("utf-8")).hexdigest()
        assert result.html_hash == expected

    def test_returns_extracted_sections_dataclass(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "10-K")
        assert isinstance(result, ExtractedSections)

    def test_unknown_filing_type_extracts_nothing(self, extractor: FilingTextExtractor) -> None:
        result = extractor.extract_sections(_10K_HTML, "8-K")
        assert result.business is None
        assert result.risk_factors is None
        assert result.mda is None
