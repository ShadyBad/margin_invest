"""Tier 1 detection — deterministic impossibility checks.

These checks catch data that is mathematically impossible for any real
publicly-traded company. All checks are deterministic (no statistical models)
and produce IMPOSSIBLE-severity flags.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.healing.models import DetectionResult, DetectionSeverity
from margin_engine.models.financial import FinancialPeriod

_IDENTITY_TOLERANCE = Decimal("0.01")


def detect_tier1(period: FinancialPeriod) -> list[DetectionResult]:
    """Run all Tier 1 (deterministic impossibility) checks on a financial period.

    Checks:
    1. Negative revenue (revenue < 0)
    2. Zero or negative shares outstanding (shares_outstanding <= 0)
    3. Accounting identity violation (L + E > A * (1 + tolerance))
    4. Stale duplicate (current == prior for all statements)

    Args:
        period: A complete financial snapshot with current and optional prior data.

    Returns:
        List of DetectionResult for each impossibility found. Empty if data is clean.
    """
    results: list[DetectionResult] = []

    # 1. Negative revenue
    if period.current_income.revenue < 0:
        results.append(
            DetectionResult(
                field_path="income_statement.revenue",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=f"Negative revenue: {period.current_income.revenue}",
                original_value=float(period.current_income.revenue),
            )
        )

    # 2. Zero or negative shares outstanding
    if period.current_income.shares_outstanding <= 0:
        results.append(
            DetectionResult(
                field_path="income_statement.shares_outstanding",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=(
                    f"Zero or negative shares outstanding: "
                    f"{period.current_income.shares_outstanding}"
                ),
                original_value=float(period.current_income.shares_outstanding),
            )
        )

    # 3. Accounting identity violation: L + E > A * (1 + tolerance)
    balance = period.current_balance
    lhs = balance.total_liabilities + balance.total_equity
    rhs = balance.total_assets * (Decimal("1") + _IDENTITY_TOLERANCE)
    if lhs > rhs:
        results.append(
            DetectionResult(
                field_path="balance_sheet.identity",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=(
                    f"Accounting identity violation: "
                    f"liabilities ({balance.total_liabilities}) + "
                    f"equity ({balance.total_equity}) = {lhs} > "
                    f"assets ({balance.total_assets}) * {Decimal('1') + _IDENTITY_TOLERANCE}"
                ),
                original_value=float(lhs),
            )
        )

    # 4. Stale duplicate: current == prior for all three statements
    if (
        period.prior_income is not None
        and period.prior_balance is not None
        and period.prior_cash_flow is not None
    ):
        current_income_dict = period.current_income.model_dump()
        prior_income_dict = period.prior_income.model_dump()
        current_balance_dict = period.current_balance.model_dump()
        prior_balance_dict = period.prior_balance.model_dump()
        current_cf_dict = period.current_cash_flow.model_dump()
        prior_cf_dict = period.prior_cash_flow.model_dump()

        if (
            current_income_dict == prior_income_dict
            and current_balance_dict == prior_balance_dict
            and current_cf_dict == prior_cf_dict
        ):
            results.append(
                DetectionResult(
                    field_path="period",
                    severity=DetectionSeverity.IMPOSSIBLE,
                    detail="Stale duplicate: current period data is identical to prior period",
                    original_value=None,
                )
            )

    return results
