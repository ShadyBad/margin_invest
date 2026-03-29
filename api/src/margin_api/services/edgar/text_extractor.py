"""Filing text extractor for SEC 10-K and 10-Q filings.

Extracts plain-text sections (Business, Risk Factors, MD&A) from raw HTML
downloaded from the SEC EDGAR filing index. Uses regex-based section boundary
detection; strips HTML tags before returning text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Maximum characters to return per section.
MAX_SECTION_CHARS = 50_000

# ---------------------------------------------------------------------------
# EDGAR index document selection
# ---------------------------------------------------------------------------

# Patterns that indicate an exhibit or ancillary document, NOT the main filing.
# Catches: ex31-1.htm, bke20230128-10kex31a.htm, exhibit_31.htm, R1.htm, etc.
_EXHIBIT_RE = re.compile(
    r"ex\d{1,4}[^/]*\.htm|exhibit|cert|^R\d+\.htm",
    re.IGNORECASE,
)


def select_primary_filing(
    items: list[dict],
    ticker: str | None = None,
) -> str | None:
    """Pick the primary 10-K/10-Q HTML document from an EDGAR index.json item list.

    Args:
        items: List of dicts from ``index_data["directory"]["item"]``,
               each with at least ``"name"`` and optionally ``"size"``.
        ticker: Ticker symbol (used to prefer files matching the ticker name).

    Returns:
        Filename of the best candidate, or None if no HTML file found.
    """
    htm_files: list[dict] = []
    for item in items:
        name = item.get("name", "")
        if not name.endswith((".htm", ".html")):
            continue
        if "index" in name.lower():
            continue
        htm_files.append(item)

    if not htm_files:
        return None

    # Score each candidate — higher is better
    def _score(item: dict) -> tuple[int, int]:
        name = item.get("name", "").lower()
        priority = 0
        is_exhibit = bool(_EXHIBIT_RE.search(name))

        # Strongly penalize exhibits and XBRL viewer stubs
        if is_exhibit:
            priority -= 100

        # Prefer files matching the ticker (only boost non-exhibits)
        if ticker and ticker.lower() in name and not is_exhibit:
            priority += 20

        # Prefer files with form type in the name (only if not an exhibit)
        normalized = name.replace("-", "").replace("_", "")
        if not is_exhibit and ("10q" in normalized or "10k" in normalized):
            priority += 10

        # Use file size as tiebreaker (actual filings are much larger)
        try:
            size = int(item.get("size", "0"))
        except (ValueError, TypeError):
            size = 0

        return (priority, size)

    best = max(htm_files, key=_score)

    # Don't return a file that scored very negatively (only exhibits found)
    score = _score(best)
    if score[0] < -50 and score[1] < 5000:
        return None

    return best.get("name")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ExtractedSections:
    """Extracted plain-text sections from a single SEC filing."""

    business: str | None
    risk_factors: str | None
    mda: str | None
    html_hash: str


# ---------------------------------------------------------------------------
# Section boundary patterns
# ---------------------------------------------------------------------------

# Patterns for 10-K sections (in order of appearance in the document).
# Each tuple is (section_name, regex_pattern_for_header).
_10K_SECTION_PATTERNS: list[tuple[str, str]] = [
    # Item 1. Business — must NOT match Item 1A
    ("business", r"item\s*1[.\s]\s*(?!a\b)business"),
    # Item 1A. Risk Factors
    ("risk_factors", r"item\s*1a[.\s]\s*risk\s*factors"),
    # Item 2. Properties — used as *end boundary* for business section implicitly;
    # we keep it here so the splitter knows where risk_factors ends.
    ("properties", r"item\s*2[.\s]\s*properties"),
    # Item 7. MD&A
    ("mda", r"item\s*7[.\s]\s*management"),
    # Item 8 is the natural end of MD&A
    ("financials", r"item\s*8[.\s]\s*financial"),
]

# Patterns for 10-Q sections.
_10Q_SECTION_PATTERNS: list[tuple[str, str]] = [
    # Part I, Item 2 — MD&A
    ("mda", r"(?:part\s*i[.\s].*?)?item\s*2[.\s]\s*management"),
    # Part I, Item 3 — Quantitative / Qualitative (end boundary for mda)
    ("quant", r"item\s*3[.\s]\s*quantitative"),
    # Part II, Item 1A — Risk Factors
    ("risk_factors", r"(?:part\s*ii[.\s].*?)?item\s*1a[.\s]\s*risk\s*factors"),
    # Part II, Item 6 — end boundary for risk_factors
    ("exhibits", r"item\s*6[.\s]\s*exhibits"),
]


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", html)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------


def _find_section_boundaries(
    text_lower: str,
    patterns: list[tuple[str, str]],
) -> dict[str, int]:
    """Find the start position of each named section in *text_lower*.

    Returns a dict mapping section_name -> char offset (or -1 if not found).
    Only the *first* match for each pattern is recorded.
    """
    positions: dict[str, int] = {}
    for name, pat in patterns:
        m = re.search(pat, text_lower)
        positions[name] = m.start() if m else -1
    return positions


def _extract_between(plain_text: str, start: int, end: int | None) -> str | None:
    """Return a slice of *plain_text* from *start* to *end*, capped at MAX_SECTION_CHARS."""
    if start < 0:
        return None
    chunk = plain_text[start:end] if end is not None else plain_text[start:]
    chunk = chunk.strip()
    if not chunk:
        return None
    return chunk[:MAX_SECTION_CHARS]


class FilingTextExtractor:
    """Extract structured text sections from SEC filing HTML."""

    def extract_sections(self, filing_html: str, filing_type: str) -> ExtractedSections:
        """Extract Item 1 / 1A / 7 from 10-K, or Item 2 / Part II 1A from 10-Q.

        Args:
            filing_html: Raw HTML string downloaded from SEC EDGAR.
            filing_type: '10-K' or '10-Q'. Any other value returns all-None.

        Returns:
            ExtractedSections with plain text (HTML stripped) and SHA-256 hash
            of the original HTML.
        """
        html_hash = hashlib.sha256(filing_html.encode("utf-8")).hexdigest()

        if filing_type not in ("10-K", "10-Q"):
            return ExtractedSections(
                business=None,
                risk_factors=None,
                mda=None,
                html_hash=html_hash,
            )

        if not filing_html.strip():
            return ExtractedSections(
                business=None,
                risk_factors=None,
                mda=None,
                html_hash=html_hash,
            )

        # Strip HTML tags for text extraction; work on the plain text version
        # for position-based slicing.  We use the lowercased version to find
        # section headers but slice the original plain-text.
        plain = _strip_html(filing_html)
        plain_lower = plain.lower()

        if filing_type == "10-K":
            return self._extract_10k(plain, plain_lower, html_hash)
        else:
            return self._extract_10q(plain, plain_lower, html_hash)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_10k(self, plain: str, plain_lower: str, html_hash: str) -> ExtractedSections:
        pos = _find_section_boundaries(plain_lower, _10K_SECTION_PATTERNS)

        business_start = pos.get("business", -1)
        risk_start = pos.get("risk_factors", -1)
        props_start = pos.get("properties", -1)
        mda_start = pos.get("mda", -1)
        fin_start = pos.get("financials", -1)

        # Business: Item 1 → Item 1A (or Item 2 if no 1A)
        if business_start >= 0:
            biz_end_candidates = [p for p in (risk_start, props_start) if p > business_start]
            biz_end = min(biz_end_candidates) if biz_end_candidates else None
            business = _extract_between(plain, business_start, biz_end)
        else:
            business = None

        # Risk Factors: Item 1A → Item 2 (properties)
        if risk_start >= 0:
            rf_end_candidates = [p for p in (props_start, mda_start) if p > risk_start]
            rf_end = min(rf_end_candidates) if rf_end_candidates else None
            risk_factors = _extract_between(plain, risk_start, rf_end)
        else:
            risk_factors = None

        # MD&A: Item 7 → Item 8
        if mda_start >= 0:
            mda_end = fin_start if fin_start > mda_start else None
            mda = _extract_between(plain, mda_start, mda_end)
        else:
            mda = None

        return ExtractedSections(
            business=business,
            risk_factors=risk_factors,
            mda=mda,
            html_hash=html_hash,
        )

    def _extract_10q(self, plain: str, plain_lower: str, html_hash: str) -> ExtractedSections:
        pos = _find_section_boundaries(plain_lower, _10Q_SECTION_PATTERNS)

        mda_start = pos.get("mda", -1)
        quant_start = pos.get("quant", -1)
        risk_start = pos.get("risk_factors", -1)
        exhibits_start = pos.get("exhibits", -1)

        # MD&A: Part I Item 2 → Item 3
        if mda_start >= 0:
            mda_end_candidates = [p for p in (quant_start, risk_start) if p > mda_start]
            mda_end = min(mda_end_candidates) if mda_end_candidates else None
            mda = _extract_between(plain, mda_start, mda_end)
        else:
            mda = None

        # Risk Factors: Part II Item 1A → Item 6
        if risk_start >= 0:
            rf_end = exhibits_start if exhibits_start > risk_start else None
            risk_factors = _extract_between(plain, risk_start, rf_end)
        else:
            risk_factors = None

        return ExtractedSections(
            business=None,  # 10-Q does not have a Business section
            risk_factors=risk_factors,
            mda=mda,
            html_hash=html_hash,
        )
