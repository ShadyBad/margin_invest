"""Tests for valuation audit models."""


from margin_engine.models.valuation_audit import MethodAudit, ValuationAudit

# ---------------------------------------------------------------------------
# MethodAudit tests
# ---------------------------------------------------------------------------


class TestMethodAudit:
    def test_defaults(self):
        """MethodAudit has sensible defaults for optional fields."""
        m = MethodAudit(method="dcf", weight=0.35)
        assert m.method == "dcf"
        assert m.weight == 0.35
        assert m.result_per_share is None
        assert m.renormalized_weight is None
        assert m.included is True
        assert m.exclusion_reason is None
        assert m.inputs == {}
        assert m.intermediates == {}

    def test_included_method_with_full_data(self):
        """MethodAudit captures all fields for an included method."""
        m = MethodAudit(
            method="dcf",
            result_per_share=185.0,
            weight=0.35,
            renormalized_weight=0.4375,
            included=True,
            inputs={"fcf": 110e9, "growth_rate": 0.05, "wacc": 0.09},
            intermediates={"pv_stage1": 1.2e12, "terminal_value": 2.8e12},
        )
        assert m.result_per_share == 185.0
        assert m.renormalized_weight == 0.4375
        assert m.inputs["wacc"] == 0.09
        assert m.intermediates["terminal_value"] == 2.8e12

    def test_excluded_method(self):
        """MethodAudit records exclusion reason when a method is dropped."""
        m = MethodAudit(
            method="dcf",
            weight=0.35,
            included=False,
            exclusion_reason="negative FCF",
        )
        assert m.included is False
        assert m.exclusion_reason == "negative FCF"
        assert m.result_per_share is None

    def test_excluded_method_outlier(self):
        """MethodAudit records outlier exclusion."""
        m = MethodAudit(
            method="ev_fcf",
            result_per_share=950.0,
            weight=0.25,
            included=False,
            exclusion_reason="15x median outlier",
            inputs={"ev": 3e12, "fcf": 110e9},
        )
        assert m.included is False
        assert m.exclusion_reason == "15x median outlier"
        assert m.result_per_share == 950.0

    def test_round_trip(self):
        """MethodAudit serializes to JSON and deserializes back."""
        m = MethodAudit(
            method="acquirers",
            result_per_share=172.50,
            weight=0.20,
            renormalized_weight=0.25,
            included=True,
            inputs={"ebit": 50e9, "ev": 2.5e12},
            intermediates={"earnings_yield": 0.02},
        )
        d = m.model_dump(mode="json")
        restored = MethodAudit.model_validate(d)
        assert restored == m

    def test_model_dump_mode_json_produces_serializable(self):
        """model_dump(mode='json') should produce a plain-dict with no Pydantic objects."""
        m = MethodAudit(method="shy", weight=0.20, inputs={"risk_free_rate": 0.043})
        d = m.model_dump(mode="json")
        # All values should be JSON-native types
        assert isinstance(d["method"], str)
        assert isinstance(d["weight"], float)
        assert isinstance(d["inputs"], dict)


# ---------------------------------------------------------------------------
# ValuationAudit tests
# ---------------------------------------------------------------------------


class TestValuationAudit:
    def test_defaults(self):
        """ValuationAudit has sensible defaults for all optional fields."""
        audit = ValuationAudit()
        assert audit.margin_invest_value is None
        assert audit.margin_of_safety is None
        assert audit.buy_price is None
        assert audit.sell_price is None
        assert audit.actual_price is None
        assert audit.methods == []
        assert audit.mos_base is None
        assert audit.mos_cv is None
        assert audit.mos_adjustment is None
        assert audit.was_clamped is False
        assert audit.clamp_reason is None

    def test_full_round_trip(self):
        """Audit captures all method details and serializes to JSON."""
        audit = ValuationAudit(
            margin_invest_value=190.25,
            margin_of_safety=0.223,
            buy_price=148.10,
            sell_price=232.60,
            actual_price=185.0,
            methods=[
                MethodAudit(
                    method="dcf",
                    result_per_share=185.0,
                    weight=0.35,
                    renormalized_weight=0.35,
                    included=True,
                    inputs={"fcf": 110e9, "growth_rate": 0.05},
                    intermediates={"pv_stage1": 1.2e12, "terminal_value": 2.8e12},
                ),
            ],
            mos_base=0.25,
            mos_cv=0.045,
            mos_adjustment=-0.0273,
        )
        d = audit.model_dump(mode="json")
        restored = ValuationAudit.model_validate(d)
        assert restored.margin_invest_value == 190.25
        assert len(restored.methods) == 1
        assert restored.methods[0].inputs["fcf"] == 110e9

    def test_multiple_methods_mixed_inclusion(self):
        """ValuationAudit handles a mix of included and excluded methods."""
        audit = ValuationAudit(
            margin_invest_value=175.50,
            margin_of_safety=0.20,
            buy_price=140.40,
            sell_price=210.60,
            actual_price=160.0,
            methods=[
                MethodAudit(
                    method="dcf",
                    result_per_share=185.0,
                    weight=0.35,
                    renormalized_weight=0.4375,
                    included=True,
                    inputs={"fcf": 110e9, "growth_rate": 0.05},
                    intermediates={"pv_stage1": 1.2e12},
                ),
                MethodAudit(
                    method="ev_fcf",
                    result_per_share=950.0,
                    weight=0.25,
                    included=False,
                    exclusion_reason="15x median outlier",
                    inputs={"ev": 3e12, "fcf": 110e9},
                ),
                MethodAudit(
                    method="acquirers",
                    result_per_share=172.50,
                    weight=0.20,
                    renormalized_weight=0.25,
                    included=True,
                    inputs={"ebit": 50e9},
                ),
                MethodAudit(
                    method="shy",
                    result_per_share=165.0,
                    weight=0.20,
                    renormalized_weight=0.3125,
                    included=True,
                    inputs={"risk_free_rate": 0.043},
                ),
            ],
            mos_base=0.25,
            mos_cv=0.12,
            mos_adjustment=0.03,
        )

        included = [m for m in audit.methods if m.included]
        excluded = [m for m in audit.methods if not m.included]
        assert len(included) == 3
        assert len(excluded) == 1
        assert excluded[0].method == "ev_fcf"
        assert excluded[0].exclusion_reason == "15x median outlier"

        # Round-trip
        d = audit.model_dump(mode="json")
        restored = ValuationAudit.model_validate(d)
        assert len(restored.methods) == 4
        assert restored.methods[1].included is False

    def test_clamped_valuation(self):
        """ValuationAudit records when margin of safety was clamped."""
        audit = ValuationAudit(
            margin_invest_value=50.0,
            margin_of_safety=0.50,
            buy_price=25.0,
            sell_price=75.0,
            actual_price=45.0,
            was_clamped=True,
            clamp_reason="MoS clamped to 0.50 maximum",
            mos_base=0.30,
            mos_cv=0.80,
            mos_adjustment=0.40,
        )
        assert audit.was_clamped is True
        assert audit.clamp_reason == "MoS clamped to 0.50 maximum"

    def test_empty_methods_list(self):
        """ValuationAudit works with no methods (e.g., all excluded)."""
        audit = ValuationAudit(
            margin_invest_value=None,
            methods=[],
        )
        assert audit.margin_invest_value is None
        assert len(audit.methods) == 0

        d = audit.model_dump(mode="json")
        restored = ValuationAudit.model_validate(d)
        assert restored.methods == []

    def test_model_dump_nested_structure(self):
        """model_dump(mode='json') produces a nested dict with methods as list of dicts."""
        audit = ValuationAudit(
            margin_invest_value=190.0,
            methods=[
                MethodAudit(method="dcf", weight=0.35, result_per_share=185.0),
                MethodAudit(method="shy", weight=0.20, result_per_share=165.0),
            ],
        )
        d = audit.model_dump(mode="json")
        assert isinstance(d["methods"], list)
        assert len(d["methods"]) == 2
        assert isinstance(d["methods"][0], dict)
        assert d["methods"][0]["method"] == "dcf"
        assert d["methods"][1]["method"] == "shy"

    def test_partial_mos_fields(self):
        """ValuationAudit allows partial MoS breakdown fields."""
        audit = ValuationAudit(
            mos_base=0.25,
            mos_cv=None,
            mos_adjustment=None,
        )
        assert audit.mos_base == 0.25
        assert audit.mos_cv is None
        assert audit.mos_adjustment is None
