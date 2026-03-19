"""Tests for thirteenf_analytics service — quarter resolution, new positions, crowded trades."""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from margin_api.db.base import Base
from margin_api.db.models import FilingMetadata, InstitutionalHolding, Manager, SecurityMaster
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


def _make_manager(id_: int, name: str, cik: str) -> Manager:
    return Manager(id=id_, name=name, cik=cik, tier="top_aum")


def _make_security(id_: int, cusip: str, ticker: str, issuer_name: str) -> SecurityMaster:
    return SecurityMaster(id=id_, cusip=cusip, ticker=ticker, issuer_name=issuer_name)


def _make_filing(id_: int, manager_id: int, period: date) -> FilingMetadata:
    return FilingMetadata(
        id=id_,
        manager_id=manager_id,
        accession_number=f"ACCN-{id_:04d}",
        filing_type="13F-HR",
        period_of_report=period,
        filed_date=period,
    )


def _make_holding(
    id_: int,
    filing_id: int,
    manager_id: int,
    security_master_id: int,
    cusip: str,
    period: date,
    shares: int = 1000,
    value_thousands: int = 100,
) -> InstitutionalHolding:
    return InstitutionalHolding(
        id=id_,
        filing_id=filing_id,
        manager_id=manager_id,
        security_master_id=security_master_id,
        cusip=cusip,
        period_of_report=period,
        shares_held=shares,
        value_thousands=value_thousands,
    )


# ---------------------------------------------------------------------------
# get_available_quarters
# ---------------------------------------------------------------------------


class TestGetAvailableQuarters:
    @pytest.mark.asyncio
    async def test_empty_table_returns_empty_list(self, session):
        from margin_api.services.thirteenf_analytics import get_available_quarters

        result = await get_available_quarters(session)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_distinct_quarters_sorted_most_recent_first(self, session):
        from margin_api.services.thirteenf_analytics import get_available_quarters

        q1 = date(2024, 3, 31)
        q2 = date(2024, 6, 30)
        q3 = date(2024, 9, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q1)
        f2 = _make_filing(2, 1, q2)
        f3 = _make_filing(3, 1, q3)
        session.add_all([mgr, sec, f1, f2, f3])
        await session.flush()

        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q1)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q2)
        # Two holdings for same q3 (should deduplicate)
        h3 = _make_holding(3, 3, 1, 1, "CUSIP001", q3)
        session.add_all([h1, h2, h3])
        await session.commit()

        result = await get_available_quarters(session)
        assert result == [q3, q2, q1]

    @pytest.mark.asyncio
    async def test_deduplicated_quarters(self, session):
        from margin_api.services.thirteenf_analytics import get_available_quarters

        q = date(2024, 6, 30)
        mgr1 = _make_manager(1, "Fund A", "0000001")
        mgr2 = _make_manager(2, "Fund B", "0000002")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q)
        f2 = _make_filing(2, 2, q)
        session.add_all([mgr1, mgr2, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q)
        h2 = _make_holding(2, 2, 2, 1, "CUSIP001", q)
        session.add_all([h1, h2])
        await session.commit()

        result = await get_available_quarters(session)
        assert result == [q]


# ---------------------------------------------------------------------------
# resolve_quarter
# ---------------------------------------------------------------------------


class TestResolveQuarter:
    @pytest.mark.asyncio
    async def test_raises_404_when_fewer_than_2_quarters(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        # No data at all
        with pytest.raises(HTTPException) as exc_info:
            await resolve_quarter(session, None)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_with_only_one_quarter(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q = date(2024, 6, 30)
        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f = _make_filing(1, 1, q)
        session.add_all([mgr, sec, f])
        await session.flush()
        h = _make_holding(1, 1, 1, 1, "CUSIP001", q)
        session.add(h)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await resolve_quarter(session, None)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_auto_detect_most_recent_two_quarters(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q1 = date(2024, 3, 31)
        q2 = date(2024, 6, 30)
        q3 = date(2024, 9, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q1)
        f2 = _make_filing(2, 1, q2)
        f3 = _make_filing(3, 1, q3)
        session.add_all([mgr, sec, f1, f2, f3])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q1)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q2)
        h3 = _make_holding(3, 3, 1, 1, "CUSIP001", q3)
        session.add_all([h1, h2, h3])
        await session.commit()

        current, prev = await resolve_quarter(session, None)
        assert current == q3
        assert prev == q2

    @pytest.mark.asyncio
    async def test_explicit_q1_parsing(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q4_prev = date(2023, 12, 31)
        q1 = date(2024, 3, 31)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q4_prev)
        f2 = _make_filing(2, 1, q1)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q4_prev)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q1)
        session.add_all([h1, h2])
        await session.commit()

        current, prev = await resolve_quarter(session, "2024-Q1")
        assert current == q1
        assert prev == q4_prev

    @pytest.mark.asyncio
    async def test_explicit_q2_parsing(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q1 = date(2024, 3, 31)
        q2 = date(2024, 6, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q1)
        f2 = _make_filing(2, 1, q2)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q1)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q2)
        session.add_all([h1, h2])
        await session.commit()

        current, prev = await resolve_quarter(session, "2024-Q2")
        assert current == q2
        assert prev == q1

    @pytest.mark.asyncio
    async def test_explicit_q3_parsing(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q2 = date(2024, 6, 30)
        q3 = date(2024, 9, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q2)
        f2 = _make_filing(2, 1, q3)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q2)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q3)
        session.add_all([h1, h2])
        await session.commit()

        current, prev = await resolve_quarter(session, "2024-Q3")
        assert current == q3
        assert prev == q2

    @pytest.mark.asyncio
    async def test_explicit_q4_parsing(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        q3 = date(2024, 9, 30)
        q4 = date(2024, 12, 31)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q3)
        f2 = _make_filing(2, 1, q4)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q3)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q4)
        session.add_all([h1, h2])
        await session.commit()

        current, prev = await resolve_quarter(session, "2024-Q4")
        assert current == q4
        assert prev == q3

    @pytest.mark.asyncio
    async def test_explicit_quarter_missing_in_db_raises_404(self, session):
        from margin_api.services.thirteenf_analytics import resolve_quarter

        # DB has Q2 and Q3 but caller asks for Q1 (no data for Q4 of prior year)
        q2 = date(2024, 6, 30)
        q3 = date(2024, 9, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q2)
        f2 = _make_filing(2, 1, q3)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q2)
        h2 = _make_holding(2, 2, 1, 1, "CUSIP001", q3)
        session.add_all([h1, h2])
        await session.commit()

        # Q1 = 2024-03-31, but no data for Q4 2023 predecessor
        with pytest.raises(HTTPException) as exc_info:
            await resolve_quarter(session, "2024-Q1")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# compute_new_positions
# ---------------------------------------------------------------------------


class TestComputeNewPositions:
    @pytest_asyncio.fixture
    async def two_quarter_session(self, session):
        """Seed two quarters of holdings data for new-positions tests."""
        q_prev = date(2024, 3, 31)
        q_curr = date(2024, 6, 30)

        mgr1 = _make_manager(1, "Berkshire Hathaway", "0001067983")
        mgr2 = _make_manager(2, "Tiger Global", "0001167483")
        mgr3 = _make_manager(3, "Viking Global", "0001103804")

        sec_aapl = _make_security(1, "037833100", "AAPL", "Apple Inc")
        sec_msft = _make_security(2, "594918104", "MSFT", "Microsoft Corp")
        sec_nvda = _make_security(3, "67066G104", "NVDA", "Nvidia Corp")

        # Filings for prev quarter
        f1_prev = _make_filing(1, 1, q_prev)
        f2_prev = _make_filing(2, 2, q_prev)
        # Filings for current quarter
        f1_curr = _make_filing(3, 1, q_curr)
        f2_curr = _make_filing(4, 2, q_curr)
        f3_curr = _make_filing(5, 3, q_curr)

        session.add_all([mgr1, mgr2, mgr3, sec_aapl, sec_msft, sec_nvda])
        session.add_all([f1_prev, f2_prev, f1_curr, f2_curr, f3_curr])
        await session.flush()

        # Prev quarter: mgr1 holds AAPL, mgr2 holds AAPL + MSFT
        h_prev_1 = _make_holding(1, 1, 1, 1, "037833100", q_prev, 1000, 200)
        h_prev_2 = _make_holding(2, 2, 2, 1, "037833100", q_prev, 500, 100)
        h_prev_3 = _make_holding(3, 2, 2, 2, "594918104", q_prev, 300, 90)

        # Current quarter:
        # mgr1 holds AAPL (not new), NVDA (new for mgr1)
        # mgr2 holds AAPL (not new), NVDA (new for mgr2), MSFT (not new)
        # mgr3 holds NVDA (new for mgr3)
        h_curr_1 = _make_holding(4, 3, 1, 1, "037833100", q_curr, 1100, 220)
        h_curr_2 = _make_holding(5, 3, 1, 3, "67066G104", q_curr, 200, 400)
        h_curr_3 = _make_holding(6, 4, 2, 1, "037833100", q_curr, 600, 120)
        h_curr_4 = _make_holding(7, 4, 2, 3, "67066G104", q_curr, 100, 200)
        h_curr_5 = _make_holding(8, 4, 2, 2, "594918104", q_curr, 350, 105)
        h_curr_6 = _make_holding(9, 5, 3, 3, "67066G104", q_curr, 50, 100)

        session.add_all([h_prev_1, h_prev_2, h_prev_3])
        session.add_all([h_curr_1, h_curr_2, h_curr_3, h_curr_4, h_curr_5, h_curr_6])
        await session.commit()

        return session, q_curr, q_prev

    @pytest.mark.asyncio
    async def test_new_positions_set_difference(self, two_quarter_session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        sess, q_curr, q_prev = two_quarter_session
        results = await compute_new_positions(sess, q_curr, q_prev)

        # Only NVDA should appear as new (3 new managers: mgr1, mgr2, mgr3)
        # AAPL was already held by both mgr1 and mgr2 in prev quarter
        # MSFT was already held by mgr2
        tickers = [r["ticker"] for r in results]
        assert "NVDA" in tickers
        assert "AAPL" not in tickers
        assert "MSFT" not in tickers

    @pytest.mark.asyncio
    async def test_new_positions_count(self, two_quarter_session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        sess, q_curr, q_prev = two_quarter_session
        results = await compute_new_positions(sess, q_curr, q_prev)

        nvda_entry = next(r for r in results if r["ticker"] == "NVDA")
        assert nvda_entry["total_new_funds"] == 3

    @pytest.mark.asyncio
    async def test_new_positions_manager_names(self, two_quarter_session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        sess, q_curr, q_prev = two_quarter_session
        results = await compute_new_positions(sess, q_curr, q_prev)

        nvda_entry = next(r for r in results if r["ticker"] == "NVDA")
        manager_names = nvda_entry["managers"]
        assert "Berkshire Hathaway" in manager_names
        assert "Tiger Global" in manager_names
        assert "Viking Global" in manager_names

    @pytest.mark.asyncio
    async def test_new_positions_value(self, two_quarter_session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        sess, q_curr, q_prev = two_quarter_session
        results = await compute_new_positions(sess, q_curr, q_prev)

        nvda_entry = next(r for r in results if r["ticker"] == "NVDA")
        # value_thousands for NVDA: 400 + 200 + 100 = 700 thousand = 0.7 million
        assert nvda_entry["total_value_millions"] == pytest.approx(0.7, rel=1e-3)

    @pytest.mark.asyncio
    async def test_no_new_positions_when_all_held_previously(self, session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        q_prev = date(2024, 3, 31)
        q_curr = date(2024, 6, 30)

        mgr = _make_manager(1, "Fund A", "0000001")
        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        f1 = _make_filing(1, 1, q_prev)
        f2 = _make_filing(2, 1, q_curr)
        session.add_all([mgr, sec, f1, f2])
        await session.flush()

        h_prev = _make_holding(1, 1, 1, 1, "CUSIP001", q_prev)
        h_curr = _make_holding(2, 2, 1, 1, "CUSIP001", q_curr)
        session.add_all([h_prev, h_curr])
        await session.commit()

        results = await compute_new_positions(session, q_curr, q_prev)
        assert results == []

    @pytest.mark.asyncio
    async def test_managers_list_capped_at_10(self, session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        q_prev = date(2024, 3, 31)
        q_curr = date(2024, 6, 30)

        sec = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        session.add(sec)

        # 15 managers all buy a new position in current quarter
        managers = [_make_manager(i, f"Fund {i}", f"{i:07d}") for i in range(1, 16)]
        filings = [_make_filing(i, i, q_curr) for i in range(1, 16)]
        session.add_all(managers)
        session.add_all(filings)
        await session.flush()

        holdings = [_make_holding(i, i, i, 1, "CUSIP001", q_curr) for i in range(1, 16)]
        session.add_all(holdings)
        await session.commit()

        results = await compute_new_positions(session, q_curr, q_prev)
        assert len(results) == 1
        aapl_entry = results[0]
        assert aapl_entry["total_new_funds"] == 15
        assert len(aapl_entry["managers"]) <= 10

    @pytest.mark.asyncio
    async def test_curated_new_funds_is_zero(self, two_quarter_session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        sess, q_curr, q_prev = two_quarter_session
        results = await compute_new_positions(sess, q_curr, q_prev)
        for r in results:
            assert r["curated_new_funds"] == 0

    @pytest.mark.asyncio
    async def test_results_sorted_by_new_manager_count_descending(self, session):
        from margin_api.services.thirteenf_analytics import compute_new_positions

        q_prev = date(2024, 3, 31)
        q_curr = date(2024, 6, 30)

        mgr1 = _make_manager(1, "Fund A", "0000001")
        mgr2 = _make_manager(2, "Fund B", "0000002")
        mgr3 = _make_manager(3, "Fund C", "0000003")
        sec_aapl = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        sec_msft = _make_security(2, "CUSIP002", "MSFT", "Microsoft Corp")
        # Filing per manager
        f1 = _make_filing(1, 1, q_curr)
        f2 = _make_filing(2, 2, q_curr)
        f3 = _make_filing(3, 3, q_curr)
        session.add_all([mgr1, mgr2, mgr3, sec_aapl, sec_msft, f1, f2, f3])
        await session.flush()

        # AAPL: 3 new managers; MSFT: 1 new manager
        h1 = _make_holding(1, 1, 1, 1, "CUSIP001", q_curr)
        h2 = _make_holding(2, 2, 2, 1, "CUSIP001", q_curr)
        h3 = _make_holding(3, 3, 3, 1, "CUSIP001", q_curr)
        h4 = _make_holding(4, 1, 1, 2, "CUSIP002", q_curr)
        session.add_all([h1, h2, h3, h4])
        await session.commit()

        results = await compute_new_positions(session, q_curr, q_prev)
        assert len(results) >= 2
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["total_new_funds"] == 3
        assert results[1]["ticker"] == "MSFT"
        assert results[1]["total_new_funds"] == 1


# ---------------------------------------------------------------------------
# compute_crowded_trades
# ---------------------------------------------------------------------------


class TestComputeCrowdedTrades:
    @pytest_asyncio.fixture
    async def crowded_session(self, session):
        """Seed a single quarter with multiple managers holding overlapping stocks."""
        q = date(2024, 6, 30)

        # 5 managers
        mgrs = [_make_manager(i, f"Fund {i}", f"{i:07d}") for i in range(1, 6)]
        # 3 securities
        sec_aapl = _make_security(1, "CUSIP001", "AAPL", "Apple Inc")
        sec_msft = _make_security(2, "CUSIP002", "MSFT", "Microsoft Corp")
        sec_nvda = _make_security(3, "CUSIP003", "NVDA", "Nvidia Corp")

        filings = [_make_filing(i, i, q) for i in range(1, 6)]

        session.add_all(mgrs + [sec_aapl, sec_msft, sec_nvda] + filings)
        await session.flush()

        # AAPL: held by 5 managers (most held)
        # MSFT: held by 3 managers
        # NVDA: held by 1 manager
        holdings = []
        hid = 1
        for mid in range(1, 6):
            holdings.append(_make_holding(hid, mid, mid, 1, "CUSIP001", q, 1000, 200))
            hid += 1
        for mid in range(1, 4):
            holdings.append(_make_holding(hid, mid, mid, 2, "CUSIP002", q, 500, 100))
            hid += 1
        holdings.append(_make_holding(hid, 1, 1, 3, "CUSIP003", q, 100, 50))

        session.add_all(holdings)
        await session.commit()

        return session, q

    @pytest.mark.asyncio
    async def test_most_held_top_entries(self, crowded_session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        sess, q = crowded_session
        most_held, crowded_trades = await compute_crowded_trades(sess, q)

        tickers_most = [r["ticker"] for r in most_held]
        assert "AAPL" in tickers_most
        assert "MSFT" in tickers_most
        assert "NVDA" in tickers_most

    @pytest.mark.asyncio
    async def test_most_held_sorted_by_holder_count(self, crowded_session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        sess, q = crowded_session
        most_held, _ = await compute_crowded_trades(sess, q)

        assert most_held[0]["ticker"] == "AAPL"
        assert most_held[0]["holder_count"] == 5
        assert most_held[1]["ticker"] == "MSFT"
        assert most_held[1]["holder_count"] == 3

    @pytest.mark.asyncio
    async def test_most_held_curated_count_is_zero(self, crowded_session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        sess, q = crowded_session
        most_held, _ = await compute_crowded_trades(sess, q)

        for entry in most_held:
            assert entry["curated_count"] == 0

    @pytest.mark.asyncio
    async def test_crowded_trades_concentration(self, crowded_session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        sess, q = crowded_session
        _, crowded_trades = await compute_crowded_trades(sess, q)

        # Total managers = 5 (all appear in at least one holding)
        aapl_entry = next(r for r in crowded_trades if r["ticker"] == "AAPL")
        # concentration_pct = 5 / 5 = 1.0
        assert aapl_entry["concentration_pct"] == pytest.approx(1.0, rel=1e-3)

        msft_entry = next(r for r in crowded_trades if r["ticker"] == "MSFT")
        # concentration_pct = 3 / 5 = 0.6
        assert msft_entry["concentration_pct"] == pytest.approx(0.6, rel=1e-3)

    @pytest.mark.asyncio
    async def test_crowded_trades_total_value(self, crowded_session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        sess, q = crowded_session
        _, crowded_trades = await compute_crowded_trades(sess, q)

        aapl_entry = next(r for r in crowded_trades if r["ticker"] == "AAPL")
        # 5 managers × value_thousands=200 = 1000 thousands = 1.0 million
        assert aapl_entry["total_value_millions"] == pytest.approx(1.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_crowded_trades_limited_to_20(self, session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        q = date(2024, 6, 30)
        mgr = _make_manager(1, "Fund A", "0000001")
        session.add(mgr)

        # 25 securities, each held by 1 manager
        securities = [
            _make_security(i, f"CUSIP{i:03d}", f"TKR{i}", f"Issuer {i}") for i in range(1, 26)
        ]
        session.add_all(securities)

        filings = [_make_filing(1, 1, q)]
        session.add_all(filings)
        await session.flush()

        holdings = [_make_holding(i, 1, 1, i, f"CUSIP{i:03d}", q) for i in range(1, 26)]
        session.add_all(holdings)
        await session.commit()

        most_held, crowded_trades = await compute_crowded_trades(session, q)
        assert len(most_held) <= 20
        assert len(crowded_trades) <= 20

    @pytest.mark.asyncio
    async def test_empty_quarter_returns_empty_lists(self, session):
        from margin_api.services.thirteenf_analytics import compute_crowded_trades

        q = date(2024, 6, 30)
        most_held, crowded_trades = await compute_crowded_trades(session, q)
        assert most_held == []
        assert crowded_trades == []
