"""Tests for the factor registry."""

from margin_engine.factors.registry import FactorMeta, FactorRegistry, default_registry


class TestFactorRegistry:
    def test_default_registry_populated(self) -> None:
        reg = default_registry()
        assert len(reg) >= 30  # at least 30 factors

    def test_register_and_get(self) -> None:
        reg = FactorRegistry()
        reg.register(FactorMeta(name="test_factor", pillar="quality"))
        assert reg.get("test_factor") is not None
        assert reg.get("test_factor").pillar == "quality"

    def test_get_missing_returns_none(self) -> None:
        reg = FactorRegistry()
        assert reg.get("nonexistent") is None

    def test_list_by_pillar(self) -> None:
        reg = default_registry()
        quality = reg.list_by_pillar("quality")
        assert len(quality) > 5
        assert all(f.pillar == "quality" for f in quality)

    def test_list_by_pillar_empty(self) -> None:
        reg = default_registry()
        unknown = reg.list_by_pillar("unknown_pillar")
        assert unknown == []

    def test_feature_names_sorted(self) -> None:
        reg = default_registry()
        names = reg.to_feature_names()
        assert names == sorted(names)

    def test_all_factors(self) -> None:
        reg = default_registry()
        all_factors = reg.all_factors()
        assert len(all_factors) == len(reg)

    def test_higher_is_better_defaults(self) -> None:
        reg = default_registry()
        accrual = reg.get("accrual_ratio")
        assert accrual is not None
        assert accrual.higher_is_better is False  # Lower accrual = better

    def test_acquirers_multiple_lower_is_better(self) -> None:
        reg = default_registry()
        acq = reg.get("acquirers_multiple")
        assert acq is not None
        assert acq.higher_is_better is False

    def test_wacc_sector_lower_is_better(self) -> None:
        reg = default_registry()
        wacc = reg.get("wacc_sector")
        assert wacc is not None
        assert wacc.higher_is_better is False

    def test_gross_profitability_higher_is_better(self) -> None:
        reg = default_registry()
        gp = reg.get("gross_profitability")
        assert gp is not None
        assert gp.higher_is_better is True

    def test_pillar_counts(self) -> None:
        reg = default_registry()
        assert len(reg.list_by_pillar("quality")) == 13
        assert len(reg.list_by_pillar("value")) == 10
        assert len(reg.list_by_pillar("momentum")) == 9
        assert len(reg.list_by_pillar("growth")) == 4
        assert len(reg.list_by_pillar("catalyst")) == 2

    def test_register_overwrites(self) -> None:
        reg = FactorRegistry()
        reg.register(FactorMeta(name="test", pillar="quality"))
        reg.register(FactorMeta(name="test", pillar="value"))
        assert reg.get("test").pillar == "value"
        assert len(reg) == 1
