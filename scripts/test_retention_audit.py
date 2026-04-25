"""Tests for retention_audit.py computation helpers.

No database required -- all tests use in-memory fake data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from retention_audit import UserMetrics, UserRow, compute_metrics, summarize, write_csv

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(d: date) -> datetime:
    """Convert a date to a tz-aware datetime at midnight UTC."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _make_user(
    user_id: int = 1,
    email: str = "test@example.com",
    created_at: date | None = None,
    last_login_at: date | None = None,
) -> UserRow:
    if created_at is None:
        created_at = date(2026, 1, 1)
    return UserRow(
        user_id=user_id,
        email=email,
        created_at=_ts(created_at),
        last_login_at=_ts(last_login_at) if last_login_at else None,
    )


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    """Unit tests for the per-user metric computation."""

    def test_never_logged_in(self) -> None:
        user = _make_user(created_at=date(2026, 1, 1), last_login_at=None)
        m = compute_metrics(user, today=date(2026, 4, 15))

        assert m.days_since_registration == 104
        assert m.distinct_active_days == 0
        assert m.weekly_active is False
        assert m.score_requests == 0

    def test_recent_login_is_weekly_active(self) -> None:
        today = date(2026, 4, 15)
        user = _make_user(
            created_at=date(2026, 2, 1),
            last_login_at=today - timedelta(days=3),
        )
        m = compute_metrics(user, today=today)

        assert m.days_since_registration == 73
        assert m.distinct_active_days == 1
        assert m.weekly_active is True

    def test_old_login_is_not_weekly_active(self) -> None:
        today = date(2026, 4, 15)
        user = _make_user(
            created_at=date(2026, 1, 1),
            last_login_at=date(2026, 3, 1),
        )
        m = compute_metrics(user, today=today)

        assert m.weekly_active is False
        assert m.distinct_active_days == 1

    def test_login_exactly_seven_days_ago(self) -> None:
        today = date(2026, 4, 15)
        user = _make_user(
            created_at=date(2026, 1, 1),
            last_login_at=today - timedelta(days=7),
        )
        m = compute_metrics(user, today=today)
        assert m.weekly_active is True

    def test_login_eight_days_ago_not_active(self) -> None:
        today = date(2026, 4, 15)
        user = _make_user(
            created_at=date(2026, 1, 1),
            last_login_at=today - timedelta(days=8),
        )
        m = compute_metrics(user, today=today)
        assert m.weekly_active is False


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


class TestSummarize:
    """Unit tests for the aggregate summary computation."""

    def test_empty_list(self) -> None:
        result = summarize([])
        assert result == {"WAU_pct": 0.0, "median_sessions": 0.0, "30day_churn_pct": 0.0}

    def test_all_active(self) -> None:
        metrics = [
            UserMetrics(
                user_id=i,
                email=f"u{i}@x.com",
                days_since_registration=60,
                distinct_active_days=1,
                weekly_active=True,
                score_requests=0,
            )
            for i in range(5)
        ]
        result = summarize(metrics)
        assert result["WAU_pct"] == 100.0
        assert result["median_sessions"] == 1.0
        assert result["30day_churn_pct"] == 0.0

    def test_all_churned(self) -> None:
        metrics = [
            UserMetrics(
                user_id=i,
                email=f"u{i}@x.com",
                days_since_registration=60,
                distinct_active_days=0,
                weekly_active=False,
                score_requests=0,
            )
            for i in range(4)
        ]
        result = summarize(metrics)
        assert result["WAU_pct"] == 0.0
        assert result["median_sessions"] == 0.0
        assert result["30day_churn_pct"] == 100.0

    def test_mixed_engagement(self) -> None:
        today = date(2026, 4, 15)
        users = [
            # Active, registered long ago
            _make_user(1, "a@x.com", date(2026, 1, 1), today - timedelta(days=2)),
            # Inactive, registered long ago -- churned
            _make_user(2, "b@x.com", date(2026, 1, 1), None),
            # Active, registered recently (<30 days) -- not eligible for churn
            _make_user(3, "c@x.com", date(2026, 3, 25), today - timedelta(days=1)),
            # Inactive, registered long ago -- churned
            _make_user(4, "d@x.com", date(2026, 2, 1), date(2026, 2, 10)),
        ]
        metrics = [compute_metrics(u, today=today) for u in users]
        result = summarize(metrics)

        # 2 of 4 are weekly_active
        assert result["WAU_pct"] == 50.0

        # Median of [1, 0, 1, 1] = 1.0
        assert result["median_sessions"] == 1.0

        # Eligible (>30 days): users 1, 2, 4.  Churned: 2, 4 (not weekly_active).
        # 2/3 = 66.7%
        assert result["30day_churn_pct"] == 66.7

    def test_no_eligible_for_churn(self) -> None:
        """All users registered <30 days ago -- churn is 0%."""
        metrics = [
            UserMetrics(
                user_id=1,
                email="new@x.com",
                days_since_registration=10,
                distinct_active_days=0,
                weekly_active=False,
                score_requests=0,
            )
        ]
        result = summarize(metrics)
        assert result["30day_churn_pct"] == 0.0


# ---------------------------------------------------------------------------
# write_csv
# ---------------------------------------------------------------------------


class TestWriteCsv:
    """Verify CSV output structure."""

    def test_csv_round_trip(self, tmp_path: object) -> None:
        import csv as csv_mod
        from pathlib import Path

        out = Path(str(tmp_path)) / "test.csv"
        metrics = [
            UserMetrics(
                user_id=42,
                email="alice@example.com",
                days_since_registration=90,
                distinct_active_days=1,
                weekly_active=True,
                score_requests=0,
            ),
            UserMetrics(
                user_id=43,
                email="bob@example.com",
                days_since_registration=60,
                distinct_active_days=0,
                weekly_active=False,
                score_requests=0,
            ),
        ]

        write_csv(metrics, path=str(out))

        with open(out) as fh:
            reader = list(csv_mod.DictReader(fh))

        assert len(reader) == 2
        assert reader[0]["user_id"] == "42"
        assert reader[0]["email"] == "alice@example.com"
        assert reader[0]["weekly_active"] == "True"
        assert reader[1]["weekly_active"] == "False"
