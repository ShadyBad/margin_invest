"""Tests for risk factor paragraph chunker."""

from __future__ import annotations

from margin_api.services.risk_diffing.chunker import chunk_risk_factors


class TestChunkRiskFactors:
    def test_splits_on_double_newline(self) -> None:
        text = "First risk factor about market conditions.\n\nSecond risk factor about competition."
        chunks = chunk_risk_factors(text)
        assert len(chunks) == 2
        assert chunks[0].text == "First risk factor about market conditions."
        assert chunks[1].text == "Second risk factor about competition."

    def test_merges_short_fragments(self) -> None:
        text = (
            "Main risk about regulatory compliance and potential fines.\n\n"
            "See above.\n\n"
            "Another distinct risk about supply chain disruptions."
        )
        chunks = chunk_risk_factors(text)
        assert len(chunks) == 2
        assert "See above." in chunks[0].text
        assert chunks[1].text == "Another distinct risk about supply chain disruptions."

    def test_drops_boilerplate_preamble(self) -> None:
        text = (
            "In addition to the other information set forth in this report, "
            "you should carefully consider the following risk factors.\n\n"
            "We face significant competition in our market."
        )
        chunks = chunk_risk_factors(text)
        assert len(chunks) == 1
        assert "competition" in chunks[0].text

    def test_assigns_sequential_indices(self) -> None:
        text = (
            "Risk factor A describes the market conditions that could affect revenue.\n\n"
            "Risk factor B describes competitive threats from new market entrants.\n\n"
            "Risk factor C describes regulatory changes that could impact operations."
        )
        chunks = chunk_risk_factors(text)
        assert [c.index for c in chunks] == [0, 1, 2]

    def test_computes_text_hash(self) -> None:
        text = "Risk factor about cybersecurity threats and data breach potential."
        chunks = chunk_risk_factors(text)
        assert len(chunks[0].text_hash) == 64  # SHA-256 hex

    def test_identical_text_produces_same_hash(self) -> None:
        text = "Risk factor about cybersecurity threats and data breach potential."
        chunks_a = chunk_risk_factors(text)
        chunks_b = chunk_risk_factors(text)
        assert chunks_a[0].text_hash == chunks_b[0].text_hash

    def test_whitespace_normalization_in_hash(self) -> None:
        text_a = "Risk factor  about  cybersecurity threats and data breach potential."
        text_b = "Risk factor about cybersecurity threats and data breach potential."
        chunks_a = chunk_risk_factors(text_a)
        chunks_b = chunk_risk_factors(text_b)
        assert chunks_a[0].text_hash == chunks_b[0].text_hash

    def test_returns_empty_list_for_none(self) -> None:
        assert chunk_risk_factors(None) == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        assert chunk_risk_factors("") == []
