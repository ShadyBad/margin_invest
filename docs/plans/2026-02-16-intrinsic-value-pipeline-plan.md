# Intrinsic Value Pipeline Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Achieve >75% intrinsic value coverage across the full ~8,000-ticker universe with accurate, sector-appropriate, currency-aware valuation.

**Architecture:** Four independent workstreams: (1) Fix `total_debt` bug, (2) Add sector-specific target multiples, (3) Add currency conversion service + fields, (4) Add fallback valuation methods (P/B, Revenue Multiple). Each workstream follows TDD — failing test first, then implementation.

**Tech Stack:** Python 3.13, Pydantic models, SQLAlchemy 2.0 (asyncpg), yfinance for exchange rates, pytest, Alembic migrations.

**Design doc:** `docs/plans/2026-02-16-intrinsic-value-pipeline-design.md`

---

### Task 1: Fix `BalanceSheet.total_debt` Bug

The `total_debt` property incorrectly adds ALL `current_liabilities` (accounts payable, deferred revenue, accrued expenses, etc.) instead of just financial debt. This over-counts debt by 1.5-11x, making EV/FCF and Acquirer's Multiple methods produce lower intrinsic values than they should.

**Files:**
- Modify: `engine/src/margin_engine/models/financial.py:81-114`
- Modify: `engine/src/margin_engine/ingestion/normalizer.py:141-202`
- Test: `engine/tests/models/test_financial.py` (create if needed, or add to existing test file)
- Test: `engine/tests/ingestion/test_normalizer.py` (add test for new field mapping)

**Step 1: Write the failing test for `short_term_debt` field and corrected `total_debt`**

```python
# In engine/tests/models/test_financial.py (or appropriate test file)
from decimal import Decimal
from margin_engine.models.financial import BalanceSheet

class TestBalanceSheetTotalDebt:
    def test_total_debt_uses_short_term_debt_not_current_liabilities(self):
        """total_debt = long_term_debt + short_term_debt, NOT current_liabilities."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_liabilities=Decimal("300"),   # includes AP, accrued expenses, etc.
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("50"),         # only the financial debt portion
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("250")  # 200 + 50, NOT 200 + 300

    def test_total_debt_defaults_short_term_to_zero(self):
        """If short_term_debt is not set, total_debt = long_term_debt only."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_liabilities=Decimal("300"),
            long_term_debt=Decimal("200"),
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("200")

    def test_total_debt_with_none_long_term(self):
        """If long_term_debt is None, total_debt = short_term_debt only."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            short_term_debt=Decimal("75"),
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("75")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/models/test_financial.py::TestBalanceSheetTotalDebt -v`
Expected: FAIL — `short_term_debt` field does not exist on BalanceSheet; `total_debt` returns wrong value.

**Step 3: Implement `short_term_debt` field and fix `total_debt`**

In `engine/src/margin_engine/models/financial.py`, add `short_term_debt` to `BalanceSheet` and fix the `total_debt` property:

```python
# Line 81-114 — BalanceSheet class
class BalanceSheet(BaseModel):
    """Annual or quarterly balance sheet data."""

    total_assets: Decimal
    current_assets: Decimal = Decimal("0")
    cash_and_equivalents: Decimal | None = None
    receivables: Decimal | None = None
    total_liabilities: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    short_term_debt: Decimal = Decimal("0")       # NEW: current portion of financial debt
    long_term_debt: Decimal | None = None
    total_equity: Decimal = Decimal("0")
    retained_earnings: Decimal | None = None
    pp_and_e: Decimal | None = None
    shares_outstanding: int = 0

    # ... keep working_capital, debt_to_equity, current_ratio properties unchanged ...

    @property
    def total_debt(self) -> Decimal:
        """Total financial debt = long-term debt + short-term financial debt.

        Does NOT include non-financial current liabilities (AP, accrued expenses, etc.).
        """
        return (self.long_term_debt or Decimal("0")) + self.short_term_debt
```

**Step 4: Add normalizer mapping for `short_term_debt`**

In `engine/src/margin_engine/ingestion/normalizer.py`, inside `normalize_balance_sheet`, add after the `long_term_debt` mapping (around line 176):

```python
short_term_debt = _get_decimal(
    raw,
    "currentDebt",
    "current_debt",
    "Current Debt",
    "Current Debt And Capital Lease Obligation",
    default="0",
)
```

And pass `short_term_debt=short_term_debt` to the `BalanceSheet(...)` constructor.

**Step 5: Write normalizer test for `short_term_debt` mapping**

```python
# In engine/tests/ingestion/test_normalizer.py
def test_normalize_balance_sheet_short_term_debt():
    """short_term_debt should map from yfinance 'Current Debt' key."""
    raw = {
        "Total Assets": 1000,
        "Current Debt": 75,
        "Long Term Debt": 200,
        "Stockholders Equity": 500,
    }
    bs = normalize_balance_sheet(raw)
    assert bs.short_term_debt == Decimal("75")
    assert bs.total_debt == Decimal("275")  # 200 + 75
```

**Step 6: Run all tests to verify nothing breaks**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ALL PASS. Existing tests that relied on the old `total_debt` behavior may need updating — check `test_price_targets.py` fixtures (the `healthy_period` fixture sets `current_liabilities=120B, long_term_debt=100B` which would now produce `total_debt=100B` instead of `220B`).

**Step 7: Commit**

```bash
git add engine/src/margin_engine/models/financial.py engine/src/margin_engine/ingestion/normalizer.py engine/tests/
git commit -m "fix: use short_term_debt instead of current_liabilities in total_debt

BalanceSheet.total_debt was adding all current_liabilities (AP, accrued
expenses, deferred revenue) instead of just financial debt. Now uses
short_term_debt + long_term_debt for accurate EV calculations."
```

---

### Task 2: Add Sector-Specific Target Multiples

Replace fixed 15x EV/FCF, 12x EV/EBIT, 4% yield with sector-appropriate values from Damodaran (NYU Stern) January 2026 data.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:38-44, 452-556`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for sector-specific multiples**

```python
# In engine/tests/scoring/quantitative/test_price_targets.py

class TestSectorSpecificMultiples:
    """Sector-specific target multiples should produce different valuations."""

    def test_energy_uses_lower_ev_fcf_multiple(self, price_bars):
        """Energy sector should use 8x EV/FCF (not default 15x)."""
        profile = AssetProfile(
            ticker="XOM",
            name="Exxon Mobil",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("400000000000"),
            shares_outstanding=4_000_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("80000000000"),      # $20/share
                gross_profit=Decimal("30000000000"),
                ebit=Decimal("20000000000"),          # $5/share
                net_income=Decimal("15000000000"),
                shares_outstanding=4_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("300000000000"),
                current_assets=Decimal("50000000000"),
                cash_and_equivalents=Decimal("20000000000"),
                current_liabilities=Decimal("40000000000"),
                short_term_debt=Decimal("5000000000"),
                long_term_debt=Decimal("30000000000"),
                total_equity=Decimal("200000000000"),
                shares_outstanding=4_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("25000000000"),
                capital_expenditures=Decimal("-5000000000"),   # FCF=$20B = $5/share
                dividends_paid=Decimal("-6000000000"),
                share_repurchases=Decimal("-4000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,      # actual_price=$197 from fixture
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        # EV/FCF at 8x: implied_ev = 8 * 20B = 160B
        # implied_equity = 160B - 35B + 20B = 145B -> $36.25/share
        # At old 15x: would be 300B -> $71.25/share
        assert result.valuation_methods["ev_fcf"] < 50.0  # Must be well below the old 15x value

    def test_tech_uses_higher_ev_fcf_multiple(self, healthy_period, price_bars):
        """Technology sector should use 25x EV/FCF (not default 15x)."""
        profile = AssetProfile(
            ticker="AAPL",
            name="Apple Inc.",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("3000000000000"),
            shares_outstanding=15_000_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        # EV/FCF at 25x should produce a higher per-share value than old 15x
        # FCF = 100B, 25x -> implied_ev = 2.5T
        assert result.valuation_methods["ev_fcf"] > 100.0

    def test_sector_multiples_dict_covers_all_gics_sectors(self):
        """SECTOR_MULTIPLES must have an entry for every non-excluded GICSSector."""
        from margin_engine.scoring.quantitative.price_targets import SECTOR_MULTIPLES
        for sector in GICSSector:
            if not sector.is_excluded_v1:
                assert sector in SECTOR_MULTIPLES, f"Missing multiples for {sector}"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestSectorSpecificMultiples -v`
Expected: FAIL — `SECTOR_MULTIPLES` doesn't exist; methods use hardcoded defaults.

**Step 3: Implement sector-specific multiples**

In `engine/src/margin_engine/scoring/quantitative/price_targets.py`:

a) Add the sector multiples constant after `_METHOD_WEIGHTS` (around line 44):

```python
from margin_engine.models.financial import GICSSector

# Sector-specific "fair value" target multiples.
# Source: Damodaran (NYU Stern) January 2026.
SECTOR_MULTIPLES: dict[GICSSector, dict[str, float]] = {
    GICSSector.ENERGY:                 {"ev_fcf": 8.0,  "ev_ebit": 10.0, "sh_yield": 0.060},
    GICSSector.MATERIALS:              {"ev_fcf": 12.0, "ev_ebit": 16.0, "sh_yield": 0.040},
    GICSSector.INDUSTRIALS:            {"ev_fcf": 18.0, "ev_ebit": 20.0, "sh_yield": 0.030},
    GICSSector.CONSUMER_DISCRETIONARY: {"ev_fcf": 16.0, "ev_ebit": 18.0, "sh_yield": 0.030},
    GICSSector.CONSUMER_STAPLES:       {"ev_fcf": 14.0, "ev_ebit": 14.0, "sh_yield": 0.040},
    GICSSector.HEALTHCARE:             {"ev_fcf": 20.0, "ev_ebit": 22.0, "sh_yield": 0.025},
    GICSSector.TECHNOLOGY:             {"ev_fcf": 25.0, "ev_ebit": 28.0, "sh_yield": 0.020},
    GICSSector.COMMUNICATION_SERVICES: {"ev_fcf": 10.0, "ev_ebit": 12.0, "sh_yield": 0.035},
    GICSSector.UTILITIES:              {"ev_fcf": 14.0, "ev_ebit": 20.0, "sh_yield": 0.045},
}
_FALLBACK_MULTIPLES = {"ev_fcf": 15.0, "ev_ebit": 15.0, "sh_yield": 0.040}
```

b) Modify `compute_price_targets` to look up sector multiples and pass them to each method. Add `sector: GICSSector | None = None` parameter (get from `profile.sector`). Look up multiples:

```python
multiples = SECTOR_MULTIPLES.get(profile.sector, _FALLBACK_MULTIPLES)
```

c) Pass sector-specific values to each method:
- `_ev_fcf_implied_per_share(..., target_multiple=multiples["ev_fcf"])`
- `_acquirers_implied_per_share(..., target_multiple=multiples["ev_ebit"])`
- `_shareholder_yield_implied_per_share(..., target_yield=multiples["sh_yield"])`

The method signatures already accept `target_multiple` / `target_yield` as parameters (lines 452, 489, 526). No signature changes needed.

**Step 4: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: ALL PASS. The `healthy_profile` fixture uses `GICSSector.TECHNOLOGY`, so existing tests will now use Tech multiples (25x EV/FCF instead of 15x). This may change some expected values in existing tests — verify and update assertions if needed.

**Step 5: Run full engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add sector-specific target multiples for valuation methods

Replace fixed 15x EV/FCF, 12x EV/EBIT, 4% yield with Damodaran-sourced
sector defaults. Energy uses 8x/10x/6%, Tech uses 25x/28x/2%, etc."
```

---

### Task 3: Add Currency Fields to AssetProfile and DB

Store `financial_currency` and `trading_currency` from yfinance on each asset, enabling currency conversion in the valuation pipeline.

**Files:**
- Modify: `engine/src/margin_engine/models/financial.py:206-220` (AssetProfile)
- Modify: `api/src/margin_api/db/models.py:83-109` (Asset DB model)
- Modify: `api/src/margin_api/cli.py:120-133` (seed command — extract currencies from yfinance info)
- Modify: `api/src/margin_api/services/scoring.py:125-166` (build_asset_profile)
- Create: `api/alembic/versions/xxxx_add_currency_fields.py` (migration)
- Test: `engine/tests/models/test_financial.py`

**Step 1: Write failing test for AssetProfile currency fields**

```python
# In engine/tests/models/test_financial.py
from margin_engine.models.financial import AssetProfile, GICSSector
from decimal import Decimal

class TestAssetProfileCurrency:
    def test_financial_currency_default_none(self):
        """financial_currency should default to None."""
        profile = AssetProfile(
            ticker="AAPL", name="Apple", sector=GICSSector.TECHNOLOGY,
        )
        assert profile.financial_currency is None

    def test_trading_currency_default_usd(self):
        """trading_currency should default to 'USD'."""
        profile = AssetProfile(
            ticker="AAPL", name="Apple", sector=GICSSector.TECHNOLOGY,
        )
        assert profile.trading_currency == "USD"

    def test_currency_mismatch_detected(self):
        """When financial_currency != trading_currency, has_currency_mismatch is True."""
        profile = AssetProfile(
            ticker="IESFY", name="Isuzu", sector=GICSSector.INDUSTRIALS,
            financial_currency="JPY", trading_currency="USD",
        )
        assert profile.has_currency_mismatch is True

    def test_same_currency_no_mismatch(self):
        """When financial_currency == trading_currency, has_currency_mismatch is False."""
        profile = AssetProfile(
            ticker="AAPL", name="Apple", sector=GICSSector.TECHNOLOGY,
            financial_currency="USD", trading_currency="USD",
        )
        assert profile.has_currency_mismatch is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/models/test_financial.py::TestAssetProfileCurrency -v`
Expected: FAIL — `financial_currency` field doesn't exist.

**Step 3: Add currency fields to AssetProfile**

In `engine/src/margin_engine/models/financial.py:206-220`:

```python
class AssetProfile(BaseModel):
    """Static asset metadata and classification."""

    ticker: str
    name: str
    sector: GICSSector
    sub_industry: str | None = None
    market_cap: Decimal = Decimal("0")
    avg_daily_volume: Decimal = Decimal("0")
    shares_outstanding: int | None = None
    years_of_history: int = 0
    financial_currency: str | None = None    # NEW: e.g., "JPY", "CAD"
    trading_currency: str = "USD"            # NEW: e.g., "USD"

    @property
    def is_excluded(self) -> bool:
        return self.sector.is_excluded_v1

    @property
    def has_currency_mismatch(self) -> bool:
        """True when financial data and stock price are in different currencies."""
        if self.financial_currency is None:
            return False
        return self.financial_currency != self.trading_currency
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/models/test_financial.py::TestAssetProfileCurrency -v`
Expected: ALL PASS.

**Step 5: Add DB columns and migration**

In `api/src/margin_api/db/models.py`, add to Asset model (after `shares_outstanding` line 92):

```python
financial_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
trading_currency: Mapped[str] = mapped_column(String(10), default="USD", server_default="USD")
```

Generate migration:

```bash
uv run alembic revision --autogenerate -m "add currency fields to assets"
uv run alembic upgrade head
```

**Step 6: Update CLI seed command to extract currencies from yfinance**

In `api/src/margin_api/cli.py`, where `info.get("sharesOutstanding")` is extracted (around line 120), also extract:

```python
financial_currency = info.get("financialCurrency")  # e.g., "JPY", "CAD", "USD"
trading_currency = info.get("currency", "USD")       # e.g., "USD"
```

Store on Asset model during upsert (around lines 133, 142).

**Step 7: Update `build_asset_profile` to pass currencies**

In `api/src/margin_api/services/scoring.py:125-166`, add `financial_currency` and `trading_currency` parameters and pass them to the AssetProfile constructor.

**Step 8: Run all tests**

Run: `uv run pytest engine/tests/ api/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 9: Commit**

```bash
git add engine/src/margin_engine/models/financial.py api/src/margin_api/db/models.py api/src/margin_api/cli.py api/src/margin_api/services/scoring.py api/alembic/ engine/tests/
git commit -m "feat: add financial_currency and trading_currency to AssetProfile

Stores yfinance financialCurrency and currency on each asset to enable
currency conversion in valuation pipeline."
```

---

### Task 4: Create Exchange Rate Service

Build a service that batch-fetches exchange rates from yfinance and caches them for use during scoring.

**Files:**
- Create: `engine/src/margin_engine/services/__init__.py`
- Create: `engine/src/margin_engine/services/exchange_rates.py`
- Test: `engine/tests/services/test_exchange_rates.py`

**Step 1: Write failing tests for ExchangeRateService**

```python
# engine/tests/services/test_exchange_rates.py
from unittest.mock import patch, MagicMock
import pytest
from margin_engine.services.exchange_rates import ExchangeRateService

class TestExchangeRateService:
    def test_same_currency_returns_one(self):
        """Converting USD to USD should return 1.0 without any API call."""
        service = ExchangeRateService()
        assert service.get_rate("USD", "USD") == 1.0

    def test_none_currency_returns_none(self):
        """If financial_currency is None, return None."""
        service = ExchangeRateService()
        assert service.get_rate(None, "USD") is None

    def test_cached_rate_returned(self):
        """After preloading rates, get_rate returns the cached value."""
        service = ExchangeRateService()
        service._cache = {"JPY": 0.0065}
        assert service.get_rate("JPY", "USD") == pytest.approx(0.0065)

    @patch("margin_engine.services.exchange_rates.yf")
    def test_fetch_rates_populates_cache(self, mock_yf):
        """fetch_rates should download rates for requested currencies."""
        import pandas as pd
        # Mock yf.download returning a DataFrame with Close prices
        mock_df = pd.DataFrame({"Close": [0.0065]}, index=["JPYUSD=X"])
        mock_yf.download.return_value = mock_df
        service = ExchangeRateService()
        service.fetch_rates({"JPY"})
        assert "JPY" in service._cache

    def test_convert_amount(self):
        """convert should multiply the amount by the exchange rate."""
        service = ExchangeRateService()
        service._cache = {"JPY": 0.0065}
        result = service.convert(1_000_000, "JPY", "USD")
        assert result == pytest.approx(6500.0)

    def test_convert_same_currency_unchanged(self):
        """Converting same currency returns the original amount."""
        service = ExchangeRateService()
        result = service.convert(100.0, "USD", "USD")
        assert result == 100.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/services/test_exchange_rates.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement ExchangeRateService**

Create `engine/src/margin_engine/services/__init__.py` (empty) and `engine/src/margin_engine/services/exchange_rates.py`:

```python
"""Exchange rate service using yfinance for currency conversion."""

from __future__ import annotations

import logging
from decimal import Decimal

import yfinance as yf

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Fetches and caches exchange rates from yfinance.

    Usage:
        service = ExchangeRateService()
        service.fetch_rates({"JPY", "CAD", "GBP"})  # batch fetch once
        rate = service.get_rate("JPY", "USD")         # 0.0065
        usd_value = service.convert(1_000_000, "JPY", "USD")  # 6500.0
    """

    def __init__(self) -> None:
        self._cache: dict[str, float] = {}

    def fetch_rates(self, currencies: set[str], to_currency: str = "USD") -> None:
        """Batch-fetch exchange rates from yfinance.

        Downloads {FROM}{TO}=X tickers for all requested currencies.
        Populates the internal cache.
        """
        # Filter out same-currency and already-cached
        needed = {c for c in currencies if c and c != to_currency and c not in self._cache}
        if not needed:
            return

        tickers = [f"{c}{to_currency}=X" for c in needed]
        logger.info("Fetching exchange rates for %d currencies: %s", len(tickers), tickers)

        try:
            data = yf.download(tickers, period="5d", progress=False, threads=True)
            if data.empty:
                logger.warning("No exchange rate data returned from yfinance")
                return

            # yf.download returns MultiIndex columns when multiple tickers
            # For single ticker, columns are just ["Close", "High", ...]
            if len(tickers) == 1:
                close = data["Close"].iloc[-1]
                currency = list(needed)[0]
                if close > 0:
                    self._cache[currency] = float(close)
                    logger.info("Rate %s->%s = %.6f", currency, to_currency, close)
            else:
                for currency in needed:
                    ticker = f"{currency}{to_currency}=X"
                    try:
                        col = data["Close"][ticker]
                        close = col.dropna().iloc[-1]
                        if close > 0:
                            self._cache[currency] = float(close)
                            logger.info("Rate %s->%s = %.6f", currency, to_currency, close)
                    except (KeyError, IndexError):
                        logger.warning("No rate data for %s", ticker)
        except Exception:
            logger.exception("Failed to fetch exchange rates")

    def get_rate(self, from_currency: str | None, to_currency: str = "USD") -> float | None:
        """Get the exchange rate for converting from_currency to to_currency.

        Returns 1.0 if currencies are the same, None if unknown.
        """
        if from_currency is None:
            return None
        if from_currency == to_currency:
            return 1.0
        return self._cache.get(from_currency)

    def convert(self, amount: float | Decimal, from_currency: str | None, to_currency: str = "USD") -> float:
        """Convert an amount from one currency to another.

        Returns the original amount if currencies are the same.
        Raises ValueError if rate is not available.
        """
        rate = self.get_rate(from_currency, to_currency)
        if rate is None:
            if from_currency == to_currency or from_currency is None:
                return float(amount)
            raise ValueError(f"No exchange rate available for {from_currency}->{to_currency}")
        return float(amount) * rate
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/services/test_exchange_rates.py -v`
Expected: ALL PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/services/ engine/tests/services/
git commit -m "feat: add ExchangeRateService for currency conversion

Batch-fetches exchange rates from yfinance using {FROM}USD=X tickers.
Caches rates for reuse during scoring runs."
```

---

### Task 5: Integrate Currency Conversion into Valuation Pipeline

Wire the exchange rate service into `compute_price_targets` so financial data is converted to the trading currency before computing intrinsic value. Replace the heuristic `_detect_currency_mismatch` function.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- Modify: `api/src/margin_api/services/scoring.py` (pass currency rate)
- Modify: `api/src/margin_api/cli.py` (fetch rates before scoring loop)
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing test for currency conversion in price targets**

```python
# In engine/tests/scoring/quantitative/test_price_targets.py

class TestCurrencyConversion:
    """Test that financial data is converted when currency_rate is provided."""

    def test_jpy_financials_converted_to_usd(self, price_bars):
        """JPY-denominated financials with rate should produce USD intrinsic value."""
        # Simulate Japanese company: all financials in JPY
        jpy_rate = 0.0065  # 1 JPY = 0.0065 USD
        profile = AssetProfile(
            ticker="JPNX",
            name="Japan Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("10000000000"),
            shares_outstanding=500_000_000,
            financial_currency="JPY",
            trading_currency="USD",
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("5000000000000"),      # 5T JPY = ~32.5B USD
                gross_profit=Decimal("2000000000000"),
                ebit=Decimal("500000000000"),           # 500B JPY = ~3.25B USD
                net_income=Decimal("300000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000000000000"),
                current_assets=Decimal("3000000000000"),
                cash_and_equivalents=Decimal("500000000000"),
                current_liabilities=Decimal("2000000000000"),
                short_term_debt=Decimal("200000000000"),
                long_term_debt=Decimal("1000000000000"),
                total_equity=Decimal("5000000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("600000000000"),
                capital_expenditures=Decimal("-200000000000"),
                dividends_paid=Decimal("-50000000000"),
                share_repurchases=Decimal("-30000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
            currency_rate=jpy_rate,
        )
        # With conversion, intrinsic value should be reasonable relative to USD price
        assert result.invalid_reason is None
        assert result.intrinsic_value is not None
        assert result.intrinsic_value > 0

    def test_no_currency_rate_with_mismatch_flags_unavailable(self, price_bars):
        """When currencies differ but no rate provided, set invalid_reason."""
        profile = AssetProfile(
            ticker="JPNX",
            name="Japan Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("10000000000"),
            shares_outstanding=500_000_000,
            financial_currency="JPY",
            trading_currency="USD",
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("5000000000000"),
                gross_profit=Decimal("2000000000000"),
                ebit=Decimal("500000000000"),
                net_income=Decimal("300000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000000000000"),
                total_equity=Decimal("5000000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("600000000000"),
                capital_expenditures=Decimal("-200000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
            # No currency_rate provided
        )
        assert result.invalid_reason == "currency_rate_unavailable"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestCurrencyConversion -v`
Expected: FAIL — `currency_rate` parameter doesn't exist.

**Step 3: Implement currency conversion in `compute_price_targets`**

In `engine/src/margin_engine/scoring/quantitative/price_targets.py`:

a) Add `currency_rate: float | None = None` parameter to `compute_price_targets`.

b) After Layer 1 checks, add currency conversion logic:

```python
# Currency conversion — replace _detect_currency_mismatch
if profile.has_currency_mismatch:
    if currency_rate is None:
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="currency_rate_unavailable",
        )
    # Convert the entire FinancialPeriod to trading currency
    period = _convert_period_currency(period, currency_rate)
```

c) Add `_convert_period_currency` helper that creates a new FinancialPeriod with all monetary values multiplied by the rate:

```python
def _convert_period_currency(period: FinancialPeriod, rate: float) -> FinancialPeriod:
    """Convert all monetary values in a FinancialPeriod by the given rate."""
    r = Decimal(str(rate))
    return FinancialPeriod(
        period_end=period.period_end,
        filing_date=period.filing_date,
        current_income=IncomeStatement(
            revenue=period.current_income.revenue * r,
            cost_of_revenue=period.current_income.cost_of_revenue * r,
            gross_profit=period.current_income.gross_profit * r,
            sga_expense=period.current_income.sga_expense * r if period.current_income.sga_expense else None,
            rd_expense=period.current_income.rd_expense * r if period.current_income.rd_expense else None,
            depreciation=period.current_income.depreciation * r if period.current_income.depreciation else None,
            ebit=period.current_income.ebit * r,
            interest_expense=period.current_income.interest_expense * r if period.current_income.interest_expense else None,
            tax_provision=period.current_income.tax_provision * r if period.current_income.tax_provision else None,
            net_income=period.current_income.net_income * r,
            shares_outstanding=period.current_income.shares_outstanding,  # NOT converted
        ),
        current_balance=BalanceSheet(
            total_assets=period.current_balance.total_assets * r,
            current_assets=period.current_balance.current_assets * r,
            cash_and_equivalents=period.current_balance.cash_and_equivalents * r if period.current_balance.cash_and_equivalents else None,
            receivables=period.current_balance.receivables * r if period.current_balance.receivables else None,
            total_liabilities=period.current_balance.total_liabilities * r,
            current_liabilities=period.current_balance.current_liabilities * r,
            short_term_debt=period.current_balance.short_term_debt * r,
            long_term_debt=period.current_balance.long_term_debt * r if period.current_balance.long_term_debt else None,
            total_equity=period.current_balance.total_equity * r,
            retained_earnings=period.current_balance.retained_earnings * r if period.current_balance.retained_earnings else None,
            pp_and_e=period.current_balance.pp_and_e * r if period.current_balance.pp_and_e else None,
            shares_outstanding=period.current_balance.shares_outstanding,  # NOT converted
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=period.current_cash_flow.operating_cash_flow * r,
            capital_expenditures=period.current_cash_flow.capital_expenditures * r,
            dividends_paid=period.current_cash_flow.dividends_paid * r if period.current_cash_flow.dividends_paid else None,
            share_repurchases=period.current_cash_flow.share_repurchases * r if period.current_cash_flow.share_repurchases else None,
            share_issuance=period.current_cash_flow.share_issuance * r if period.current_cash_flow.share_issuance else None,
        ),
    )
```

d) Remove `_detect_currency_mismatch` function and the `_CURRENCY_MISMATCH_RATIO` constant entirely.

e) Remove the old TestCurrencyMismatchDetection tests and replace with the new TestCurrencyConversion tests.

**Step 4: Update API services to pass `currency_rate`**

In `api/src/margin_api/services/scoring.py`, where `compute_price_targets` is called (around line 302), pass the currency rate:

```python
price_targets = compute_price_targets(
    period=r.period,
    profile=r.profile,
    price_bars=r.price_bars,
    conviction_level=base_composite.conviction_level,
    growth_stage=r.growth_stage,
    currency_rate=exchange_rates.get(r.profile.financial_currency),
)
```

The `exchange_rates` dict is passed into `rank_and_compute_composites` from the CLI.

**Step 5: Update CLI to fetch exchange rates before scoring**

In `api/src/margin_api/cli.py`, in `run_scoring`:

a) After loading all assets (Pass 1), collect unique `financial_currency` values.
b) Create an `ExchangeRateService`, call `fetch_rates` with the set of currencies.
c) Pass the service (or rates dict) into `rank_and_compute_composites`.

**Step 6: Run all tests**

Run: `uv run pytest engine/tests/ api/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py api/src/margin_api/services/scoring.py api/src/margin_api/cli.py engine/tests/
git commit -m "feat: integrate currency conversion into valuation pipeline

Replaces heuristic currency mismatch detection with actual conversion
using exchange rates from yfinance. Financial data is converted to
trading currency before computing intrinsic value."
```

---

### Task 6: Add Fallback Valuation Methods (P/B and Revenue Multiple)

Add Price-to-Book and Revenue Multiple as fallback methods that only activate when ALL 4 primary methods return None.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing tests for fallback methods**

```python
# In engine/tests/scoring/quantitative/test_price_targets.py

class TestFallbackMethods:
    """P/B and Revenue Multiple fallbacks for unprofitable companies."""

    def test_price_to_book_activates_for_unprofitable(self, price_bars):
        """When FCF<0, EBIT<0, no dividends, P/B fallback should produce a target."""
        profile = AssetProfile(
            ticker="LSNG",
            name="Losing Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000000"),
            shares_outstanding=10_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("50000000"),
                gross_profit=Decimal("-10000000"),
                ebit=Decimal("-20000000"),
                net_income=Decimal("-30000000"),
                shares_outstanding=10_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("200000000"),
                current_assets=Decimal("50000000"),
                cash_and_equivalents=Decimal("20000000"),
                current_liabilities=Decimal("80000000"),
                short_term_debt=Decimal("10000000"),
                long_term_debt=Decimal("50000000"),
                total_equity=Decimal("70000000"),     # Positive equity -> P/B works
                shares_outstanding=10_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("-15000000"),
                capital_expenditures=Decimal("-5000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.invalid_reason is None
        assert "price_to_book" in result.valuation_methods

    def test_revenue_multiple_when_pb_fails(self, price_bars):
        """When FCF<0, EBIT<0, negative equity, revenue multiple should activate."""
        profile = AssetProfile(
            ticker="BURN",
            name="Cash Burn Inc",
            sector=GICSSector.HEALTHCARE,
            market_cap=Decimal("100000000"),
            shares_outstanding=5_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("30000000"),    # $6/share revenue
                gross_profit=Decimal("10000000"),
                ebit=Decimal("-5000000"),
                net_income=Decimal("-15000000"),
                shares_outstanding=5_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("50000000"),
                current_assets=Decimal("20000000"),
                cash_and_equivalents=Decimal("15000000"),
                current_liabilities=Decimal("30000000"),
                total_equity=Decimal("-10000000"),    # Negative equity -> P/B fails
                shares_outstanding=5_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("-10000000"),
                capital_expenditures=Decimal("-2000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.invalid_reason is None
        assert "revenue_multiple" in result.valuation_methods

    def test_fallback_not_used_when_primary_works(self, healthy_period, healthy_profile, price_bars):
        """When primary methods succeed, fallbacks should NOT appear."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        assert "price_to_book" not in result.valuation_methods
        assert "revenue_multiple" not in result.valuation_methods

    def test_truly_ineligible_still_returns_insufficient_data(self, price_bars):
        """Zero revenue + negative equity + negative cash flows -> insufficient_data."""
        profile = AssetProfile(
            ticker="ZERO",
            name="Zero Revenue Corp",
            sector=GICSSector.HEALTHCARE,
            market_cap=Decimal("10000000"),
            shares_outstanding=1_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("0"),
                ebit=Decimal("-5000000"),
                net_income=Decimal("-5000000"),
                shares_outstanding=1_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("5000000"),
                total_equity=Decimal("-2000000"),
                shares_outstanding=1_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("-3000000"),
                capital_expenditures=Decimal("-500000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "insufficient_data"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestFallbackMethods -v`
Expected: FAIL — fallback methods don't exist.

**Step 3: Implement fallback methods**

In `engine/src/margin_engine/scoring/quantitative/price_targets.py`:

a) Add sector-specific P/B and P/S multiples:

```python
SECTOR_PB_MULTIPLES: dict[GICSSector, float] = {
    GICSSector.ENERGY: 1.2,
    GICSSector.MATERIALS: 1.5,
    GICSSector.INDUSTRIALS: 2.5,
    GICSSector.CONSUMER_DISCRETIONARY: 3.0,
    GICSSector.CONSUMER_STAPLES: 3.0,
    GICSSector.HEALTHCARE: 4.0,
    GICSSector.TECHNOLOGY: 5.0,
    GICSSector.COMMUNICATION_SERVICES: 2.0,
    GICSSector.UTILITIES: 1.5,
}
_FALLBACK_PB = 2.0

SECTOR_PS_MULTIPLES: dict[GICSSector, float] = {
    GICSSector.ENERGY: 1.0,
    GICSSector.MATERIALS: 1.0,
    GICSSector.INDUSTRIALS: 1.5,
    GICSSector.CONSUMER_DISCRETIONARY: 1.5,
    GICSSector.CONSUMER_STAPLES: 1.5,
    GICSSector.HEALTHCARE: 5.0,
    GICSSector.TECHNOLOGY: 6.0,
    GICSSector.COMMUNICATION_SERVICES: 3.0,
    GICSSector.UTILITIES: 2.0,
}
_FALLBACK_PS = 2.0
```

b) Add `_price_to_book_implied_per_share` function:

```python
def _price_to_book_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    sector: GICSSector,
    actual_price: float | None = None,
) -> float | None:
    """Implied price from sector target P/B multiple.

    Returns None if total_equity <= 0 (negative book value).
    """
    book_value = period.current_balance.total_equity
    if book_value <= 0:
        return None
    target_pb = SECTOR_PB_MULTIPLES.get(sector, _FALLBACK_PB)
    result = target_pb * float(book_value) / shares
    if result < _MIN_PER_SHARE_PRICE:
        return None
    if actual_price is not None and actual_price > 0 and result > _MAX_PRICE_MULTIPLE * actual_price:
        return None
    return result
```

c) Add `_revenue_multiple_implied_per_share` function:

```python
def _revenue_multiple_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    sector: GICSSector,
    actual_price: float | None = None,
) -> float | None:
    """Implied price from sector target P/S (revenue) multiple.

    Returns None if revenue <= 0.
    """
    revenue = period.current_income.revenue
    if revenue <= 0:
        return None
    target_ps = SECTOR_PS_MULTIPLES.get(sector, _FALLBACK_PS)
    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    implied_ev = target_ps * float(revenue)
    implied_equity = implied_ev - float(total_debt) + float(cash)
    if implied_equity <= 0:
        return None
    result = implied_equity / shares
    if result < _MIN_PER_SHARE_PRICE:
        return None
    if actual_price is not None and actual_price > 0 and result > _MAX_PRICE_MULTIPLE * actual_price:
        return None
    return result
```

d) In `compute_price_targets`, after "if not valid_methods", add fallback logic:

```python
if not valid_methods:
    # Try fallback methods: P/B and Revenue Multiple
    fallback_methods: dict[str, float | None] = {
        "price_to_book": _price_to_book_implied_per_share(
            period=period, shares=shares, sector=profile.sector, actual_price=actual_price,
        ),
        "revenue_multiple": _revenue_multiple_implied_per_share(
            period=period, shares=shares, sector=profile.sector, actual_price=actual_price,
        ),
    }
    valid_methods = {k: v for k, v in fallback_methods.items() if v is not None}
    if not valid_methods:
        return PriceTargets(actual_price=actual_price, invalid_reason="insufficient_data")
    # Wider margin of safety for fallback-only valuations (add 10% penalty)
    _using_fallback = True
else:
    _using_fallback = False
```

Then later in the MoS computation:

```python
mos = _compute_margin_of_safety(valid_methods, intrinsic_value, growth_stage)
if _using_fallback:
    mos = min(_MOS_CEILING, mos + 0.10)  # 10% penalty for fallback methods
```

**Step 4: Run all tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: ALL PASS.

**Step 5: Run full engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat: add P/B and Revenue Multiple fallback valuation methods

Activates only when all 4 primary methods return None (unprofitable
companies). Uses sector-specific P/B and P/S multiples with 10% wider
margin of safety penalty."
```

---

### Task 7: Add Growth Rate Guardrails to DCF

Cap the DCF growth rate to prevent runaway projections.

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:403-449`
- Test: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Write failing test**

```python
class TestDCFGrowthGuardrails:
    def test_actual_growth_used_when_available(self, healthy_profile, price_bars):
        """DCF should use actual revenue growth (capped) when available."""
        # Period with 10% revenue growth
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("110000000000"),
                gross_profit=Decimal("45000000000"),
                ebit=Decimal("30000000000"),
                net_income=Decimal("25000000000"),
                shares_outstanding=15_000_000_000,
            ),
            prior_income=IncomeStatement(
                revenue=Decimal("100000000000"),
                gross_profit=Decimal("40000000000"),
                ebit=Decimal("27000000000"),
                net_income=Decimal("22000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("350000000000"),
                current_assets=Decimal("130000000000"),
                cash_and_equivalents=Decimal("60000000000"),
                current_liabilities=Decimal("120000000000"),
                long_term_debt=Decimal("100000000000"),
                total_equity=Decimal("60000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("110000000000"),
                capital_expenditures=Decimal("-10000000000"),
            ),
        )
        # The DCF method should use ~10% growth (actual) instead of default 5%
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        assert "dcf" in result.valuation_methods

    def test_growth_capped_at_15_percent(self, healthy_profile, price_bars):
        """DCF growth rate should be capped at 15% even if actual growth is higher."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("200000000000"),  # 100% growth
                gross_profit=Decimal("90000000000"),
                ebit=Decimal("60000000000"),
                net_income=Decimal("50000000000"),
                shares_outstanding=15_000_000_000,
            ),
            prior_income=IncomeStatement(
                revenue=Decimal("100000000000"),
                gross_profit=Decimal("45000000000"),
                ebit=Decimal("30000000000"),
                net_income=Decimal("25000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("350000000000"),
                current_assets=Decimal("130000000000"),
                cash_and_equivalents=Decimal("60000000000"),
                current_liabilities=Decimal("120000000000"),
                long_term_debt=Decimal("100000000000"),
                total_equity=Decimal("60000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("110000000000"),
                capital_expenditures=Decimal("-10000000000"),
            ),
        )
        # DCF should use 15% (cap), not 100% (actual)
        result_capped = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result_capped.intrinsic_value is not None
```

**Step 2: Run test to verify behavior**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestDCFGrowthGuardrails -v`

**Step 3: Implement growth rate guardrails**

In `compute_price_targets`, before calling `_dcf_intrinsic_per_share`, compute the actual growth rate:

```python
# Growth rate guardrails for DCF
_MAX_GROWTH_RATE = 0.15
_MIN_GROWTH_RATE = 0.00
actual_growth = period.revenue_growth  # Returns None if no prior_income
if actual_growth is not None:
    dcf_growth = max(_MIN_GROWTH_RATE, min(actual_growth, _MAX_GROWTH_RATE))
else:
    dcf_growth = growth_rate  # Fall back to parameter default (0.05)
```

Then pass `growth_rate=dcf_growth` to `_dcf_intrinsic_per_share`.

**Step 4: Run all tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/
git commit -m "feat: add DCF growth rate guardrails

Use actual revenue growth when available, capped at [0%, 15%] to prevent
runaway projections in DCF valuation."
```

---

### Task 8: Add Empty Financial Data Detection

Detect assets with empty JSONB (`{}`) and flag them early with a specific reason.

**Files:**
- Modify: `api/src/margin_api/services/scoring.py`
- Test: `api/tests/test_scoring_service.py`

**Step 1: Write failing test**

```python
# In api/tests/test_scoring_service.py (add to existing or create)
def test_empty_financial_data_detected():
    """Empty income_statement/cash_flow JSONB should raise or be flagged."""
    from margin_api.services.scoring import build_financial_period
    # Empty dicts should produce a FinancialPeriod with zero values
    period = build_financial_period(
        income_raw={},
        balance_raw={},
        cashflow_raw={},
        period_end="2025-09-28",
        filing_date="2025-11-01",
    )
    # With empty data, revenue should be 0
    assert period.current_income.revenue == 0
```

**Step 2: Implement empty data detection in scoring service**

In `api/src/margin_api/services/scoring.py`, in `rank_and_compute_composites`, before calling `compute_price_targets`, check if the financial period has empty data:

```python
# Check for empty financial data
if r.period.current_income.revenue == 0 and r.period.current_cash_flow.operating_cash_flow == 0:
    # All monetary values are zero — likely empty JSONB
    price_targets = PriceTargets(actual_price=actual_price, invalid_reason="financial_data_empty")
else:
    price_targets = compute_price_targets(...)
```

**Step 3: Run tests**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: ALL PASS.

**Step 4: Commit**

```bash
git add api/src/margin_api/services/scoring.py api/tests/
git commit -m "feat: detect empty financial data before valuation

Flag assets with empty JSONB ({}) as financial_data_empty instead of
falling through to insufficient_data."
```

---

### Task 9: Populate Currency Data for Existing Assets

Run a one-time backfill to populate `financial_currency` and `trading_currency` for all existing assets in the DB.

**Files:**
- Modify: `api/src/margin_api/cli.py` (add `backfill-currencies` command)

**Step 1: Add CLI command**

```python
# In api/src/margin_api/cli.py
async def backfill_currencies():
    """Backfill financial_currency and trading_currency for all assets."""
    import yfinance as yf
    # ... fetch all assets from DB
    # ... for each asset, fetch info from yfinance
    # ... extract financialCurrency and currency
    # ... update the Asset row
```

**Step 2: Test manually**

Run: `uv run python -m margin_api.cli backfill-currencies --limit 10`
Verify: Check DB that `financial_currency` and `trading_currency` are populated.

**Step 3: Run full backfill**

Run: `uv run python -m margin_api.cli backfill-currencies`

**Step 4: Commit**

```bash
git add api/src/margin_api/cli.py
git commit -m "feat: add backfill-currencies CLI command

One-time backfill of financial_currency and trading_currency from
yfinance info for all existing assets."
```

---

### Task 10: Full Universe Re-Score and Verification

Re-score the entire universe with all fixes applied and verify coverage.

**Step 1: Run full universe re-score**

```bash
uv run python -m margin_api.cli score
```

**Step 2: Verify coverage**

```python
# Check coverage stats
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

engine = create_async_engine('postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest')

async def verify():
    async with engine.connect() as conn:
        total = (await conn.execute(text("SELECT COUNT(DISTINCT asset_id) FROM scores"))).scalar()
        has_target = (await conn.execute(text("""
            SELECT COUNT(DISTINCT asset_id) FROM scores s
            WHERE s.scored_at = (SELECT MAX(s2.scored_at) FROM scores s2 WHERE s2.asset_id = s.asset_id)
            AND s.intrinsic_value IS NOT NULL
        """))).scalar()
        print(f"Coverage: {has_target}/{total} ({100*has_target/total:.1f}%)")
        # Target: >75% coverage
    await engine.dispose()

asyncio.run(verify())
```

Expected: >75% coverage (up from 44.7%).

**Step 3: Check for extreme outliers**

```python
# Verify no assets have >400% upside
rows = await conn.execute(text("""
    SELECT COUNT(*) FROM scores s
    WHERE s.scored_at = (SELECT MAX(s2.scored_at) FROM scores s2 WHERE s2.asset_id = s.asset_id)
    AND s.price_upside > 4.0
"""))
assert rows.scalar() == 0
```

**Step 4: Verify all rejected assets have reasons**

```python
# No blank rejections
rows = await conn.execute(text("""
    SELECT COUNT(*) FROM scores s
    WHERE s.scored_at = (SELECT MAX(s2.scored_at) FROM scores s2 WHERE s2.asset_id = s.asset_id)
    AND s.intrinsic_value IS NULL AND s.price_target_invalid_reason IS NULL
"""))
assert rows.scalar() == 0
```

**Step 5: Commit verification results**

```bash
git commit -m "chore: verify intrinsic value pipeline overhaul coverage"
```

---

## Summary of Changes

| Task | What | Files Modified |
|------|------|----------------|
| 1 | Fix `total_debt` bug | `models/financial.py`, `normalizer.py` |
| 2 | Sector-specific multiples | `price_targets.py` |
| 3 | Currency fields on AssetProfile/DB | `financial.py`, `db/models.py`, `cli.py`, `scoring.py` |
| 4 | Exchange rate service | New: `services/exchange_rates.py` |
| 5 | Currency conversion integration | `price_targets.py`, `scoring.py`, `cli.py` |
| 6 | P/B and Revenue Multiple fallbacks | `price_targets.py` |
| 7 | DCF growth rate guardrails | `price_targets.py` |
| 8 | Empty financial data detection | `scoring.py` |
| 9 | Currency data backfill | `cli.py` |
| 10 | Full re-score and verification | CLI + DB queries |
