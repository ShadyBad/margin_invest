"""Investigation: Do capital-light compounders pass Gate 2 (compounding_power > 0.04)?

Gate 2 in v3_cascade.py requires compounding_power > 0.04.
compute_compounding_power() = incremental_ROIC * reinvestment_rate * stability

Capital-light compounders (Apple, Visa) have:
- Very high ROIC (excellent incremental ROIC and stability)
- Minimal growth capex (capex ~ depreciation, so growth_capex near 0)
- R&D growth as reinvestment (captured, but small relative to NOPAT)
- Result: reinvestment_rate is very low, dragging compounding_power below 0.04

This test file documents the finding with realistic financial profiles.
"""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.v3_intermediates import compute_compounding_power

GATE_2_THRESHOLD = 0.04


def _make_period(
    *,
    period_end: str,
    revenue: Decimal,
    ebit: Decimal,
    net_income: Decimal,
    depreciation: Decimal | None = None,
    rd_expense: Decimal | None = None,
    total_equity: Decimal,
    long_term_debt: Decimal = Decimal("0"),
    short_term_debt: Decimal = Decimal("0"),
    cash_and_equivalents: Decimal = Decimal("0"),
    total_assets: Decimal = Decimal("0"),
    capital_expenditures: Decimal = Decimal("0"),
    operating_cash_flow: Decimal = Decimal("0"),
    prior_rd_expense: Decimal | None = None,
    tax_provision: Decimal | None = None,
) -> FinancialPeriod:
    """Build a FinancialPeriod with full control over R&D and prior_income."""
    current_income = IncomeStatement(
        revenue=revenue,
        ebit=ebit,
        net_income=net_income,
        depreciation=depreciation,
        rd_expense=rd_expense,
        tax_provision=tax_provision,
        shares_outstanding=1000,
    )
    prior_income = None
    if prior_rd_expense is not None:
        prior_income = IncomeStatement(
            revenue=revenue * Decimal("0.95"),  # prior revenue ~5% less
            ebit=ebit * Decimal("0.95"),
            net_income=net_income * Decimal("0.95"),
            rd_expense=prior_rd_expense,
            shares_outstanding=1000,
        )
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=current_income,
        prior_income=prior_income,
        current_balance=BalanceSheet(
            total_assets=total_assets if total_assets else total_equity * 2,
            total_equity=total_equity,
            long_term_debt=long_term_debt,
            short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=1000,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


def _build_apple_history() -> FinancialHistory:
    """Build Apple-like 5-year financial history.

    Apple characteristics (FY2020-FY2024 approximate):
    - Revenue: ~$275B -> ~$390B
    - EBIT: ~$66B -> ~$125B (operating leverage)
    - NOPAT: ~$52B -> ~$99B (at ~21% tax rate)
    - Capex: ~$7-11B, Depreciation: ~$11B (growth_capex near 0)
    - R&D: ~$19B -> ~$30B (real R&D reinvestment over time)
    - Equity: ~$65B -> ~$57B (buybacks shrink equity!)
    - Total debt: ~$112B -> ~$105B
    - Cash: ~$38B -> ~$30B
    - IC = equity + debt - cash, stays around $135-140B
    - Very high ROIC (~37-70%), extremely stable
    """
    periods = [
        _make_period(
            period_end="2020-09-26",
            revenue=Decimal("274500"),  # $274.5B in millions
            ebit=Decimal("66288"),
            net_income=Decimal("57411"),
            depreciation=Decimal("11056"),
            rd_expense=Decimal("18752"),
            total_equity=Decimal("65339"),
            long_term_debt=Decimal("98667"),
            short_term_debt=Decimal("13769"),
            cash_and_equivalents=Decimal("38016"),
            capital_expenditures=Decimal("-7309"),
            operating_cash_flow=Decimal("80674"),
            prior_rd_expense=None,  # No prior for earliest period
            tax_provision=Decimal("9680"),
        ),
        _make_period(
            period_end="2021-09-25",
            revenue=Decimal("365817"),
            ebit=Decimal("108949"),
            net_income=Decimal("94680"),
            depreciation=Decimal("11284"),
            rd_expense=Decimal("21914"),
            total_equity=Decimal("63090"),
            long_term_debt=Decimal("109106"),
            short_term_debt=Decimal("15613"),
            cash_and_equivalents=Decimal("34940"),
            capital_expenditures=Decimal("-11085"),
            operating_cash_flow=Decimal("104038"),
            prior_rd_expense=Decimal("18752"),
            tax_provision=Decimal("14527"),
        ),
        _make_period(
            period_end="2022-09-24",
            revenue=Decimal("394328"),
            ebit=Decimal("119437"),
            net_income=Decimal("99803"),
            depreciation=Decimal("11104"),
            rd_expense=Decimal("26251"),
            total_equity=Decimal("50672"),
            long_term_debt=Decimal("98959"),
            short_term_debt=Decimal("21110"),
            cash_and_equivalents=Decimal("23646"),
            capital_expenditures=Decimal("-10708"),
            operating_cash_flow=Decimal("122151"),
            prior_rd_expense=Decimal("21914"),
            tax_provision=Decimal("19300"),
        ),
        _make_period(
            period_end="2023-09-30",
            revenue=Decimal("383285"),
            ebit=Decimal("114301"),
            net_income=Decimal("96995"),
            depreciation=Decimal("11519"),
            rd_expense=Decimal("29915"),
            total_equity=Decimal("62146"),
            long_term_debt=Decimal("95281"),
            short_term_debt=Decimal("15807"),
            cash_and_equivalents=Decimal("29965"),
            capital_expenditures=Decimal("-10959"),
            operating_cash_flow=Decimal("110543"),
            prior_rd_expense=Decimal("26251"),
            tax_provision=Decimal("16741"),
        ),
        _make_period(
            period_end="2024-09-28",
            revenue=Decimal("391035"),
            ebit=Decimal("123216"),
            net_income=Decimal("93736"),
            depreciation=Decimal("11445"),
            rd_expense=Decimal("31370"),
            total_equity=Decimal("56950"),
            long_term_debt=Decimal("96800"),
            short_term_debt=Decimal("10900"),
            cash_and_equivalents=Decimal("29943"),
            capital_expenditures=Decimal("-9959"),
            operating_cash_flow=Decimal("118254"),
            prior_rd_expense=Decimal("29915"),
            tax_provision=Decimal("29749"),
        ),
    ]
    return FinancialHistory(ticker="AAPL_LIKE", periods=periods)


def _build_visa_history() -> FinancialHistory:
    """Build Visa-like 5-year financial history.

    Visa characteristics (FY2020-FY2024 approximate):
    - Revenue: ~$22B -> ~$36B
    - EBIT: ~$14B -> ~$23B
    - NOPAT: ~$11B -> ~$18B (at ~21% tax rate)
    - Capex: ~$0.7-1.0B, Depreciation: ~$0.7-0.9B (growth_capex near 0)
    - R&D: ~$1.0B -> ~$1.4B (modest R&D spend)
    - Equity: ~$36B -> ~$39B
    - Total debt: ~$22B -> ~$21B
    - Cash: ~$16B -> ~$10B
    - IC = equity + debt - cash, ~$42-50B
    - Very high ROIC (~22-36%), extremely stable
    """
    periods = [
        _make_period(
            period_end="2020-09-30",
            revenue=Decimal("21846"),  # $21.8B in millions
            ebit=Decimal("14062"),
            net_income=Decimal("10866"),
            depreciation=Decimal("712"),
            rd_expense=Decimal("1010"),
            total_equity=Decimal("36210"),
            long_term_debt=Decimal("22034"),
            short_term_debt=Decimal("0"),
            cash_and_equivalents=Decimal("16289"),
            capital_expenditures=Decimal("-694"),
            operating_cash_flow=Decimal("10109"),
            prior_rd_expense=None,
            tax_provision=Decimal("2687"),
        ),
        _make_period(
            period_end="2021-09-30",
            revenue=Decimal("24105"),
            ebit=Decimal("15800"),
            net_income=Decimal("12311"),
            depreciation=Decimal("756"),
            rd_expense=Decimal("1118"),
            total_equity=Decimal("37589"),
            long_term_debt=Decimal("20077"),
            short_term_debt=Decimal("2999"),
            cash_and_equivalents=Decimal("16487"),
            capital_expenditures=Decimal("-756"),
            operating_cash_flow=Decimal("14510"),
            prior_rd_expense=Decimal("1010"),
            tax_provision=Decimal("3752"),
        ),
        _make_period(
            period_end="2022-09-30",
            revenue=Decimal("29310"),
            ebit=Decimal("18814"),
            net_income=Decimal("14957"),
            depreciation=Decimal("808"),
            rd_expense=Decimal("1227"),
            total_equity=Decimal("35581"),
            long_term_debt=Decimal("20200"),
            short_term_debt=Decimal("2250"),
            cash_and_equivalents=Decimal("15689"),
            capital_expenditures=Decimal("-810"),
            operating_cash_flow=Decimal("17868"),
            prior_rd_expense=Decimal("1118"),
            tax_provision=Decimal("3262"),
        ),
        _make_period(
            period_end="2023-09-30",
            revenue=Decimal("32653"),
            ebit=Decimal("21024"),
            net_income=Decimal("17273"),
            depreciation=Decimal("870"),
            rd_expense=Decimal("1332"),
            total_equity=Decimal("37840"),
            long_term_debt=Decimal("20437"),
            short_term_debt=Decimal("1749"),
            cash_and_equivalents=Decimal("12028"),
            capital_expenditures=Decimal("-960"),
            operating_cash_flow=Decimal("19668"),
            prior_rd_expense=Decimal("1227"),
            tax_provision=Decimal("3710"),
        ),
        _make_period(
            period_end="2024-09-30",
            revenue=Decimal("35926"),
            ebit=Decimal("23349"),
            net_income=Decimal("19743"),
            depreciation=Decimal("920"),
            rd_expense=Decimal("1432"),
            total_equity=Decimal("38982"),
            long_term_debt=Decimal("20836"),
            short_term_debt=Decimal("1749"),
            cash_and_equivalents=Decimal("10109"),
            capital_expenditures=Decimal("-1020"),
            operating_cash_flow=Decimal("22006"),
            prior_rd_expense=Decimal("1332"),
            tax_provision=Decimal("3959"),
        ),
    ]
    return FinancialHistory(ticker="V_LIKE", periods=periods)


class TestCapitalLightCompoundersGate2:
    """Investigation: capital-light compounders vs Gate 2 threshold (0.04).

    FINDING: Both Apple-like and Visa-like profiles produce compounding_power
    FAR BELOW 0.04 because their reinvestment_rate is tiny.

    The formula compounding_power = inc_roic * reinvestment_rate * stability
    penalizes capital-light business models that return cash to shareholders
    (buybacks, dividends) rather than reinvesting in capex or R&D growth.

    This is a structural flaw in the formula for capital-light compounders.
    """

    def test_apple_compounding_power_components(self):
        """Trace Apple-like compounding_power step by step.

        Expected computation (approximate):
        - Earliest IC = 65339 + 98667 + 13769 - 38016 = 139,759
        - Latest IC = 56950 + 96800 + 10900 - 29943 = 134,707
        - delta_IC = 134,707 - 139,759 = -5,052 (NEGATIVE!)
        - Because Apple buys back stock aggressively, IC actually SHRINKS.
        - This means incremental ROIC has delta_IC <= 0, returning 0.0 immediately.
        """
        history = _build_apple_history()
        result = compute_compounding_power(history)

        # Document the result
        print("\n=== APPLE-LIKE COMPOUNDING POWER ===")
        print(f"compounding_power = {result:.6f}")
        print(f"Gate 2 threshold  = {GATE_2_THRESHOLD}")
        print(f"Passes Gate 2?    = {result > GATE_2_THRESHOLD}")

        # Apple's IC shrinks due to massive buybacks. delta_IC < 0 => returns 0.0.
        # This is an even MORE severe problem than just low reinvestment_rate.
        # The function returns 0.0 because delta_IC <= 0.
        assert result == 0.0, f"Expected 0.0 (delta_IC negative due to buybacks), got {result}"

    def test_apple_shrinking_invested_capital(self):
        """Verify Apple's invested capital shrinks due to buybacks.

        Apple FY2020 IC = equity(65339) + debt(98667+13769) - cash(38016) = 139,759
        Apple FY2024 IC = equity(56950) + debt(96800+10900) - cash(29943) = 134,707
        Delta IC = -5,052 (negative!)

        This is the root cause: the function requires growing IC to compute
        incremental ROIC, but buyback-heavy companies shrink their IC.
        """
        history = _build_apple_history()
        earliest = history.periods[0]
        latest = history.periods[-1]

        # Compute IC for earliest and latest
        cb_e = earliest.current_balance
        ic_earliest = (
            float(cb_e.total_equity) + float(cb_e.total_debt) - float(cb_e.cash_and_equivalents)
        )

        cb_l = latest.current_balance
        ic_latest = (
            float(cb_l.total_equity) + float(cb_l.total_debt) - float(cb_l.cash_and_equivalents)
        )

        delta_ic = ic_latest - ic_earliest
        print(f"\nApple IC earliest: {ic_earliest:,.0f}")
        print(f"Apple IC latest:   {ic_latest:,.0f}")
        print(f"Apple delta IC:    {delta_ic:,.0f}")

        # IC shrinks — this is the structural issue
        assert delta_ic < 0, f"Expected negative delta_IC, got {delta_ic}"

    def test_visa_compounding_power_components(self):
        """Trace Visa-like compounding_power step by step.

        Expected computation (approximate):
        - Earliest IC = 36210 + 22034 + 0 - 16289 = 41,955
        - Latest IC = 38982 + 20836 + 1749 - 10109 = 51,458
        - delta_IC = 51,458 - 41,955 = 9,503
        - NOPAT_earliest = 14062 * (1 - tax_rate_e), NOPAT_latest = 23349 * (1 - tax_rate_l)
        - inc_roic = (NOPAT_l - NOPAT_e) / delta_IC

        For reinvestment_rate (latest period):
        - capex = abs(-1020) = 1020
        - depreciation = 920
        - growth_capex = max(1020 - 920, 0) = 100
        - current_rd = 1432, prior_rd = 1332
        - inflation_adj_prior = 1332 * 1.03 = 1371.96
        - rd_growth = max(1432 - 1371.96, 0) = 60.04
        - total_reinvestment = 100 + 60.04 = 160.04
        - NOPAT_latest ~ 23349 * 0.79 = 18,445.71
        - reinvestment_rate = 160.04 / 18445.71 = 0.00868

        So compounding_power ~ inc_roic * 0.00868 * stability
        Even with perfect inc_roic of 1.0 and stability of 1.0,
        result would be only 0.00868 — well below 0.04.
        """
        history = _build_visa_history()
        result = compute_compounding_power(history)

        # Document the result
        print("\n=== VISA-LIKE COMPOUNDING POWER ===")
        print(f"compounding_power = {result:.6f}")
        print(f"Gate 2 threshold  = {GATE_2_THRESHOLD}")
        print(f"Passes Gate 2?    = {result > GATE_2_THRESHOLD}")

        # Assert it fails Gate 2
        assert result < GATE_2_THRESHOLD, (
            f"Expected compounding_power < {GATE_2_THRESHOLD}, got {result}"
        )

    def test_visa_reinvestment_rate_details(self):
        """Manually verify Visa's reinvestment components are tiny."""
        history = _build_visa_history()
        latest = history.periods[-1]

        capex = abs(float(latest.current_cash_flow.capital_expenditures))
        depreciation = float(latest.current_income.depreciation or Decimal("0"))
        growth_capex = max(capex - depreciation, 0.0)

        current_rd = float(latest.current_income.rd_expense)
        prior_rd = float(latest.prior_income.rd_expense)
        inflation_adj_prior = prior_rd * 1.03
        rd_growth = max(current_rd - inflation_adj_prior, 0.0)

        total_reinvestment = growth_capex + rd_growth

        # NOPAT for latest period
        ebit = float(latest.current_income.ebit)
        tax_rate = latest.current_income.effective_tax_rate
        nopat = ebit * (1.0 - tax_rate)

        reinvestment_rate = total_reinvestment / nopat if nopat > 0 else 0.0

        print("\n=== VISA REINVESTMENT BREAKDOWN ===")
        print(f"Capex:              {capex:,.0f}")
        print(f"Depreciation:       {depreciation:,.0f}")
        print(f"Growth capex:       {growth_capex:,.0f}")
        print(f"Current R&D:        {current_rd:,.0f}")
        print(f"Prior R&D (adj):    {inflation_adj_prior:,.2f}")
        print(f"R&D growth:         {rd_growth:,.2f}")
        print(f"Total reinvestment: {total_reinvestment:,.2f}")
        print(f"NOPAT:              {nopat:,.2f}")
        print(f"Reinvestment rate:  {reinvestment_rate:.6f}")
        print(f"Max possible CP:    {reinvestment_rate:.6f} (if inc_roic=1, stability=1)")

        # Reinvestment rate is well below 4% (Gate 2 needs CP > 0.04)
        assert reinvestment_rate < 0.02, (
            f"Expected very low reinvestment rate, got {reinvestment_rate}"
        )

    def test_gate2_requires_heavy_reinvestment(self):
        """Show that passing Gate 2 requires substantial capital reinvestment.

        To get compounding_power > 0.04 with inc_roic = 0.5, stability = 0.9:
          0.04 = 0.5 * reinvestment_rate * 0.9
          reinvestment_rate = 0.04 / (0.5 * 0.9) = 0.089 (8.9%)

        Capital-light compounders typically have reinvestment_rate < 2%,
        making it mathematically impossible to reach 0.04.
        """
        # For a capital-heavy compounder (e.g., a manufacturer), this works fine.
        # But for Apple: reinvestment_rate ~ 0 (delta_IC < 0, returns 0.0)
        # For Visa: reinvestment_rate ~ 0.009

        # Minimum reinvestment_rate to pass Gate 2 at various inc_roic / stability combos
        scenarios = [
            (0.3, 0.9, "Good inc_roic, high stability"),
            (0.5, 0.9, "Strong inc_roic, high stability"),
            (1.0, 1.0, "Perfect inc_roic and stability"),
        ]
        print("\n=== MINIMUM REINVESTMENT RATE TO PASS GATE 2 ===")
        for inc_roic, stability, desc in scenarios:
            min_rr = GATE_2_THRESHOLD / (inc_roic * stability)
            print(f"{desc}: min reinvestment_rate = {min_rr:.4f} ({min_rr * 100:.1f}%)")

        # Even with PERFECT inc_roic=1.0 and stability=1.0, need 4% reinvestment.
        # Visa's ~0.9% reinvestment rate would need inc_roic > 4.5 (impossible).
        min_rr_perfect = GATE_2_THRESHOLD / (1.0 * 1.0)
        assert min_rr_perfect == pytest.approx(0.04), "Sanity check"

    def test_summary_of_findings(self):
        """Summary: both Apple-like and Visa-like profiles FAIL Gate 2.

        Root causes:
        1. Apple: delta_IC < 0 (buybacks shrink invested capital) => returns 0.0
        2. Visa: reinvestment_rate ~ 0.009 => compounding_power ~ 0.006, far below 0.04

        FIX NEEDED: The compounding_power formula structurally penalizes
        capital-light business models. Two specific issues:

        Issue A - Shrinking IC: Companies with aggressive buybacks have
            delta_IC < 0, causing compute_compounding_power() to return 0.0.
            These are among the BEST compounders (Apple returns > cost of capital
            and distributes excess to shareholders).

        Issue B - Low reinvestment_rate denominator: Capital-light compounders
            return cash via buybacks/dividends rather than reinvesting in capex.
            Their reinvestment_rate is structurally < 2%, making it impossible
            to achieve compounding_power > 0.04 even with perfect inc_roic
            and stability.

        Possible fix directions:
        - Include buybacks + dividends as "shareholder reinvestment" in the
          reinvestment calculation
        - Use ROIC level directly (not just incremental) for capital-light models
        - Add a capital-light bypass: if ROIC > X% and NOPAT growing, skip Gate 2
        - Replace reinvestment_rate with total_return_on_capital metric
          that captures both reinvested and returned capital
        """
        apple_history = _build_apple_history()
        visa_history = _build_visa_history()

        apple_cp = compute_compounding_power(apple_history)
        visa_cp = compute_compounding_power(visa_history)

        print("\n=== INVESTIGATION SUMMARY ===")
        apple_gate = "PASS" if apple_cp > GATE_2_THRESHOLD else "FAIL"
        visa_gate = "PASS" if visa_cp > GATE_2_THRESHOLD else "FAIL"
        print(f"Apple-like compounding_power: {apple_cp:.6f}  ({apple_gate})")
        print(f"Visa-like compounding_power:  {visa_cp:.6f}  ({visa_gate})")
        print(f"Gate 2 threshold:             {GATE_2_THRESHOLD}")
        print("\nVERDICT: FIX NEEDED — both capital-light compounders fail Gate 2")

        assert apple_cp < GATE_2_THRESHOLD
        assert visa_cp < GATE_2_THRESHOLD
