"""Healing pipeline orchestrator — coordinates detection, correction, and circuit breakers.

The HealingPipeline is the single entry point for the self-healing data layer.
It runs all three detection tiers, checks circuit breakers, applies corrections,
and returns a complete HealingResult with an optionally corrected FinancialPeriod.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from margin_engine.healing.circuit_breakers import check_sector_breadth
from margin_engine.healing.correction import apply_corrections
from margin_engine.healing.detection import detect_tier1, detect_tier2, detect_tier3
from margin_engine.healing.models import (
    EXCLUDED_FIELDS,
    CorrectionEvent,
    DetectionResult,
    HealingConfig,
    SectorDistribution,
)
from margin_engine.models.financial import FinancialPeriod


class HealingResult(BaseModel):
    """Complete result of the healing pipeline for a single financial period."""

    period: FinancialPeriod
    detections: list[DetectionResult] = []
    corrections: list[CorrectionEvent] = []
    excluded: bool = False
    breadth_suspended: bool = False


class HealingPipeline:
    """Orchestrates anomaly detection, circuit breakers, and corrections.

    Usage::

        pipeline = HealingPipeline(config=HealingConfig())
        result = pipeline.heal(period, sector, sector_distributions, ...)
    """

    def __init__(self, config: HealingConfig | None = None) -> None:
        self.config = config or HealingConfig()

    def heal(
        self,
        period: FinancialPeriod,
        sector: str,
        sector_distributions: list[SectorDistribution],
        prior_sector_distributions: list[SectorDistribution],
        ticker_history: dict[str, list[float]],
        secondary_values: dict[str, float] | None,
        prior_valid_values: dict[str, float] | None,
        sector_ticker_count: int = 0,
        sector_flagged_tickers: set[str] | None = None,
    ) -> HealingResult:
        """Run the full healing pipeline on a single financial period.

        Steps:
        1. Run Tier 1 detection (deterministic impossibility checks).
        2. Extract field values from the period for statistical detection.
        3. Run Tier 2 detection (MAD-based outlier detection).
        4. Run Tier 3 detection (cross-sectional consistency).
        5. If no detections, return early with clean result.
        6. Check sector breadth circuit breaker — if tripped, return with
           detections but no corrections (breadth_suspended=True).
        7. Apply L1/L2/L3 correction hierarchy.
        8. Check for uncorrected excluded fields → set excluded=True.
        9. Apply corrections to a copy of the period.
        10. Return HealingResult.

        Args:
            period: The financial period to heal.
            sector: GICS sector name.
            sector_distributions: Current cross-sectional distributions.
            prior_sector_distributions: Prior period distributions (for Tier 3).
            ticker_history: Field path -> historical values for self-history.
            secondary_values: Alternative data source values for L1 correction.
            prior_valid_values: Last known good values for L2 carry-forward.
            sector_ticker_count: Total tickers in this sector (for breadth check).
            sector_flagged_tickers: Set of ticker symbols already flagged in this sector.

        Returns:
            HealingResult with detections, corrections, and optionally modified period.
        """
        all_detections: list[DetectionResult] = []

        # Step 1: Tier 1 — deterministic impossibility checks
        tier1_flags = detect_tier1(period)
        all_detections.extend(tier1_flags)

        # Step 2: Extract field values for statistical tiers
        field_values = self._extract_field_values(period)

        # Step 3: Tier 2 — MAD-based outlier detection
        tier2_flags = detect_tier2(field_values, sector_distributions, self.config)
        all_detections.extend(tier2_flags)

        # Step 4: Tier 3 — cross-sectional consistency
        tier3_flags = detect_tier3(
            field_values,
            ticker_history,
            sector_distributions,
            prior_sector_distributions,
            self.config,
        )
        all_detections.extend(tier3_flags)

        # Step 5: No detections → clean result
        if not all_detections:
            return HealingResult(period=period)

        # Step 6: Sector breadth circuit breaker
        flagged = sector_flagged_tickers or set()
        if check_sector_breadth(flagged, sector_ticker_count, self.config):
            return HealingResult(
                period=period,
                detections=all_detections,
                corrections=[],
                breadth_suspended=True,
            )

        # Step 7: Apply corrections
        corrections = apply_corrections(
            all_detections,
            self.config,
            secondary_values=secondary_values,
            prior_valid_values=prior_valid_values,
            sector_distributions=sector_distributions,
        )

        # Step 8: Check for uncorrected detections on excluded fields
        corrected_fields = {c.field_path for c in corrections}
        excluded = False
        for detection in all_detections:
            if detection.field_path not in corrected_fields:
                # Check if the field's basename is in EXCLUDED_FIELDS
                basename = detection.field_path.rsplit(".", 1)[-1]
                if basename in EXCLUDED_FIELDS:
                    excluded = True
                    break

        # Step 9: Apply corrections to a copy of the period
        healed_period = period.model_copy(deep=True)
        for correction in corrections:
            healed_period = self._apply_correction_to_period(healed_period, correction)

        # Step 10: Return result
        return HealingResult(
            period=healed_period,
            detections=all_detections,
            corrections=corrections,
            excluded=excluded,
            breadth_suspended=False,
        )

    def _extract_field_values(self, period: FinancialPeriod) -> dict[str, float]:
        """Extract numeric field values from a FinancialPeriod for Tier 2/3 detection.

        Extracts:
        - income_statement.gross_margin (skipped if revenue == 0)
        - income_statement.net_margin (skipped if revenue == 0)
        - balance_sheet.debt_to_equity
        - balance_sheet.current_ratio

        Args:
            period: The financial period to extract values from.

        Returns:
            Dict mapping field_path to float value.
        """
        values: dict[str, float] = {}

        # Margin fields — skip if revenue is zero (margins would be meaningless)
        if period.current_income.revenue != 0:
            values["income_statement.gross_margin"] = period.current_income.gross_margin
            values["income_statement.net_margin"] = period.current_income.net_margin

        # Balance sheet ratios
        de = period.current_balance.debt_to_equity
        if de != float("inf"):
            values["balance_sheet.debt_to_equity"] = de

        cr = period.current_balance.current_ratio
        if cr != float("inf"):
            values["balance_sheet.current_ratio"] = cr

        return values

    def _apply_correction_to_period(
        self,
        period: FinancialPeriod,
        event: CorrectionEvent,
    ) -> FinancialPeriod:
        """Apply a single CorrectionEvent to a FinancialPeriod.

        Handles field paths like "income_statement.revenue" by navigating
        to the correct sub-model and setting the corrected value, respecting
        the field's type (Decimal for monetary fields, int for counts, float for ratios).

        Args:
            period: The period to modify (should already be a deep copy).
            event: The correction event with field_path and corrected_value.

        Returns:
            The modified period (same object, mutated in place).
        """
        parts = event.field_path.split(".", 1)
        if len(parts) != 2:
            return period

        section, field_name = parts

        # Map section name to period attribute
        section_map = {
            "income_statement": "current_income",
            "balance_sheet": "current_balance",
            "cash_flow": "current_cash_flow",
        }

        attr_name = section_map.get(section)
        if attr_name is None:
            return period

        sub_model = getattr(period, attr_name, None)
        if sub_model is None:
            return period

        # Check if the field exists on the sub-model
        if not hasattr(sub_model, field_name):
            return period

        # Determine the correct type for the field
        current_value = getattr(sub_model, field_name)
        if isinstance(current_value, Decimal):
            corrected = Decimal(str(event.corrected_value))
        elif isinstance(current_value, int):
            corrected = int(event.corrected_value)
        else:
            corrected = event.corrected_value

        # Use model copy to set the value (Pydantic models may be frozen)
        # Build a dict of current values, override the target field
        sub_dict = sub_model.model_dump()
        sub_dict[field_name] = corrected
        new_sub = type(sub_model)(**sub_dict)
        object.__setattr__(period, attr_name, new_sub)

        return period
