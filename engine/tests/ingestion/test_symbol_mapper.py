"""Tests for cross-provider symbol translation."""

from pathlib import Path
from textwrap import dedent

from margin_engine.ingestion.symbol_mapper import SymbolMapper

OVERRIDES = {
    "BRK-B": {"polygon": "BRK.B"},
    "BF-B": {"polygon": "BF.B"},
}


class TestToProviderPassThrough:
    """Pass-through default — no override exists for ticker/provider."""

    def test_unknown_ticker_returns_itself(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("AAPL", "fmp") == "AAPL"

    def test_unknown_provider_returns_itself(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("AAPL", "polygon") == "AAPL"

    def test_no_overrides_at_all(self) -> None:
        mapper = SymbolMapper()
        assert mapper.to_provider("MSFT", "polygon") == "MSFT"


class TestToProviderOverride:
    """Override found — provider-specific symbol returned."""

    def test_brk_b_polygon(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("BRK-B", "polygon") == "BRK.B"

    def test_bf_b_polygon(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("BF-B", "polygon") == "BF.B"


class TestToProviderMissingProvider:
    """Override exists for ticker but not for this provider — falls through."""

    def test_brk_b_unknown_provider(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("BRK-B", "unknown") == "BRK-B"

    def test_brk_b_fmp_falls_through(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.to_provider("BRK-B", "fmp") == "BRK-B"


class TestFromProviderRoundtrip:
    """Reverse lookup — provider symbol back to canonical."""

    def test_brk_b_roundtrip(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        provider_sym = mapper.to_provider("BRK-B", "polygon")
        canonical = mapper.from_provider(provider_sym, "polygon")
        assert canonical == "BRK-B"

    def test_bf_b_roundtrip(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        provider_sym = mapper.to_provider("BF-B", "polygon")
        canonical = mapper.from_provider(provider_sym, "polygon")
        assert canonical == "BF-B"

    def test_from_provider_direct(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.from_provider("BRK.B", "polygon") == "BRK-B"


class TestFromProviderPassThrough:
    """No reverse mapping — returns input unchanged."""

    def test_aapl_fmp(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.from_provider("AAPL", "fmp") == "AAPL"

    def test_aapl_polygon(self) -> None:
        mapper = SymbolMapper(overrides=OVERRIDES)
        assert mapper.from_provider("AAPL", "polygon") == "AAPL"

    def test_no_overrides(self) -> None:
        mapper = SymbolMapper()
        assert mapper.from_provider("MSFT", "polygon") == "MSFT"


class TestFromYaml:
    """Loading overrides from a YAML file."""

    def test_loads_overrides(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            overrides:
              BRK-B:
                polygon: "BRK.B"
              BF-B:
                polygon: "BF.B"
        """)
        yaml_file = tmp_path / "overrides.yaml"
        yaml_file.write_text(yaml_content)

        mapper = SymbolMapper.from_yaml(yaml_file)
        assert mapper.to_provider("BRK-B", "polygon") == "BRK.B"
        assert mapper.from_provider("BRK.B", "polygon") == "BRK-B"

    def test_roundtrip_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            overrides:
              BRK-B:
                polygon: "BRK.B"
        """)
        yaml_file = tmp_path / "overrides.yaml"
        yaml_file.write_text(yaml_content)

        mapper = SymbolMapper.from_yaml(yaml_file)
        assert mapper.to_provider("AAPL", "polygon") == "AAPL"
        assert mapper.from_provider("AAPL", "polygon") == "AAPL"

    def test_empty_overrides_section(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            overrides: {}
        """)
        yaml_file = tmp_path / "overrides.yaml"
        yaml_file.write_text(yaml_content)

        mapper = SymbolMapper.from_yaml(yaml_file)
        assert mapper.to_provider("AAPL", "polygon") == "AAPL"
