"""Tests for the daily picks archive Pydantic snapshot models (v1.0.0)."""

from datetime import datetime, timezone

import pytest

from margin_api.archiver.models import (
    ExclusionSummary,
    HashChain,
    MLDetail,
    ModifierDetail,
    PickEntry,
    PillarDetail,
    SnapshotPayload,
    TrackScoreDetail,
)

_TS = datetime(2026, 4, 21, 20, 30, 0, tzinfo=timezone.utc)


def _make_pick(rank: int = 1, *, null_ml: bool = False) -> PickEntry:
    ml = (
        MLDetail(alpha=None, confidence=None, override="none")
        if null_ml
        else MLDetail(alpha=0.12, confidence=0.87, override="none")
    )
    return PickEntry(
        rank=rank,
        ticker="AAPL",
        composite_score=82.5,
        conviction="strong",
        opportunity_type="compounder",
        style="growth",
        track_scores={
            "value": TrackScoreDetail(score=78.0, qualifies=True, gates_passed=4, total_gates=5),
            "momentum": TrackScoreDetail(score=90.0, qualifies=True, gates_passed=5, total_gates=5),
        },
        pillars={
            "quality": PillarDetail(factors={"roic": 0.34, "gm": 0.45}),
            "growth": PillarDetail(factors={"rev_growth": 0.12}),
        },
        modifiers=ModifierDetail(
            liquidity=1.0, insider_signal=0.5, inflection=0.0, tam=0.2, anti_consensus=0.0
        ),
        ml=ml,
        sector="Technology",
        market_cap_usd=3_000_000_000_000,
        price_at_close=189.50,
    )


def _make_snapshot(*, genesis: bool = True) -> SnapshotPayload:
    hash_chain = (
        HashChain(previous_date=None, previous_payload_hash=None)
        if genesis
        else HashChain(previous_date="2026-04-20", previous_payload_hash="abc123deadbeef")
    )
    return SnapshotPayload(
        snapshot_date="2026-04-21",
        generated_at_utc=_TS,
        market_close_time=_TS,
        universe_size=500,
        model_hash="modelabc123",
        input_data_hash="inputxyz456",
        top_picks=[_make_pick(1), _make_pick(2)],
        excluded_count=10,
        exclusion_summary=ExclusionSummary(conviction_none=10),
        hash_chain=hash_chain,
        payload_hash="deadbeef1234567890",
    )


# ---------------------------------------------------------------------------
# TrackScoreDetail
# ---------------------------------------------------------------------------


class TestTrackScoreDetail:
    def test_construction_and_field_access(self) -> None:
        detail = TrackScoreDetail(score=75.0, qualifies=True, gates_passed=3, total_gates=5)
        assert detail.score == 75.0
        assert detail.qualifies is True
        assert detail.gates_passed == 3
        assert detail.total_gates == 5

    def test_not_qualifies(self) -> None:
        detail = TrackScoreDetail(score=40.0, qualifies=False, gates_passed=1, total_gates=5)
        assert detail.qualifies is False

    def test_zero_gates(self) -> None:
        detail = TrackScoreDetail(score=0.0, qualifies=False, gates_passed=0, total_gates=0)
        assert detail.gates_passed == 0
        assert detail.total_gates == 0


# ---------------------------------------------------------------------------
# PickEntry
# ---------------------------------------------------------------------------


class TestPickEntry:
    def test_serialization_roundtrip(self) -> None:
        pick = _make_pick(1)
        dumped = pick.model_dump()
        reconstructed = PickEntry.model_validate(dumped)
        assert reconstructed.ticker == pick.ticker
        assert reconstructed.composite_score == pick.composite_score
        assert reconstructed.conviction == pick.conviction
        assert reconstructed.rank == pick.rank

    def test_track_scores_preserved(self) -> None:
        pick = _make_pick(1)
        assert "value" in pick.track_scores
        assert pick.track_scores["value"].score == 78.0
        assert pick.track_scores["momentum"].qualifies is True

    def test_pillars_preserved(self) -> None:
        pick = _make_pick(1)
        assert "quality" in pick.pillars
        assert pick.pillars["quality"].factors["roic"] == 0.34

    def test_modifiers_defaults(self) -> None:
        mod = ModifierDetail()
        assert mod.liquidity == 0.0
        assert mod.insider_signal == 0.0
        assert mod.inflection == 0.0
        assert mod.tam == 0.0
        assert mod.anti_consensus == 0.0

    def test_nullable_ml_fields(self) -> None:
        pick = _make_pick(1, null_ml=True)
        assert pick.ml.alpha is None
        assert pick.ml.confidence is None
        assert pick.ml.override == "none"

    def test_nullable_ml_roundtrip(self) -> None:
        pick = _make_pick(1, null_ml=True)
        dumped = pick.model_dump()
        reconstructed = PickEntry.model_validate(dumped)
        assert reconstructed.ml.alpha is None
        assert reconstructed.ml.confidence is None

    def test_rank_must_be_at_least_1(self) -> None:
        with pytest.raises(Exception):
            _make_pick(0)

    def test_market_cap_usd_is_int(self) -> None:
        pick = _make_pick(1)
        assert isinstance(pick.market_cap_usd, int)
        assert pick.market_cap_usd == 3_000_000_000_000

    def test_price_at_close(self) -> None:
        pick = _make_pick(1)
        assert pick.price_at_close == 189.50


# ---------------------------------------------------------------------------
# ExclusionSummary
# ---------------------------------------------------------------------------


class TestExclusionSummary:
    def test_field_access(self) -> None:
        summary = ExclusionSummary(conviction_none=7)
        assert summary.conviction_none == 7

    def test_default_zero(self) -> None:
        summary = ExclusionSummary()
        assert summary.conviction_none == 0


# ---------------------------------------------------------------------------
# HashChain
# ---------------------------------------------------------------------------


class TestHashChain:
    def test_genesis_chain(self) -> None:
        chain = HashChain(previous_date=None, previous_payload_hash=None)
        assert chain.previous_date is None
        assert chain.previous_payload_hash is None

    def test_linked_chain(self) -> None:
        chain = HashChain(previous_date="2026-04-20", previous_payload_hash="abc123deadbeef")
        assert chain.previous_date == "2026-04-20"
        assert chain.previous_payload_hash == "abc123deadbeef"

    def test_defaults_are_none(self) -> None:
        chain = HashChain()
        assert chain.previous_date is None
        assert chain.previous_payload_hash is None


# ---------------------------------------------------------------------------
# SnapshotPayload
# ---------------------------------------------------------------------------


class TestSnapshotPayload:
    def test_genesis_snapshot_roundtrip(self) -> None:
        snap = _make_snapshot(genesis=True)
        dumped = snap.model_dump()
        reconstructed = SnapshotPayload.model_validate(dumped)
        assert reconstructed.snapshot_date == "2026-04-21"
        assert reconstructed.snapshot_version == "1.0.0"
        assert reconstructed.methodology_version == "4.0.0"
        assert reconstructed.hash_chain.previous_date is None
        assert reconstructed.hash_chain.previous_payload_hash is None

    def test_linked_snapshot_roundtrip(self) -> None:
        snap = _make_snapshot(genesis=False)
        dumped = snap.model_dump()
        reconstructed = SnapshotPayload.model_validate(dumped)
        assert reconstructed.hash_chain.previous_date == "2026-04-20"
        assert reconstructed.hash_chain.previous_payload_hash == "abc123deadbeef"

    def test_top_picks_count(self) -> None:
        snap = _make_snapshot()
        assert len(snap.top_picks) == 2
        assert snap.top_picks[0].rank == 1
        assert snap.top_picks[1].rank == 2

    def test_universe_size(self) -> None:
        snap = _make_snapshot()
        assert snap.universe_size == 500

    def test_excluded_count(self) -> None:
        snap = _make_snapshot()
        assert snap.excluded_count == 10
        assert snap.exclusion_summary.conviction_none == 10

    def test_hashes_present(self) -> None:
        snap = _make_snapshot()
        assert snap.model_hash == "modelabc123"
        assert snap.input_data_hash == "inputxyz456"
        assert snap.payload_hash == "deadbeef1234567890"

    def test_timestamps(self) -> None:
        snap = _make_snapshot()
        assert snap.generated_at_utc == _TS
        assert snap.market_close_time == _TS

    def test_default_versions(self) -> None:
        snap = _make_snapshot()
        assert snap.snapshot_version == "1.0.0"
        assert snap.methodology_version == "4.0.0"
