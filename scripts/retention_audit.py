#!/usr/bin/env python3
"""Retention audit -- measures engagement for existing users.

Queries the users table for accounts registered before 2026-04-01 and computes
engagement metrics from the available DB signals (created_at, last_login_at).

Usage:
    uv run python scripts/retention_audit.py

Output:
    /tmp/retention-audit.csv  -- one row per user
    stdout summary line       -- WAU_pct, median_sessions, 30day_churn_pct

Limitations:
    - The DB stores only `last_login_at` (single timestamp), not per-session
      history. `distinct_active_days` will be 0 or 1. Richer session-level
      data would require PostHog Events API integration.
    - `score_requests` is always 0 because there is no request-log table.
      A future iteration can pull this from PostHog.
"""

from __future__ import annotations

import asyncio
import csv
import os
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Pure computation helpers (no DB, fully testable)
# ---------------------------------------------------------------------------


@dataclass
class UserRow:
    """Minimal representation of a user row for metric computation."""

    user_id: int
    email: str
    created_at: datetime
    last_login_at: datetime | None


@dataclass
class UserMetrics:
    """Computed engagement metrics for a single user."""

    user_id: int
    email: str
    days_since_registration: int
    distinct_active_days: int
    weekly_active: bool
    score_requests: int


def compute_metrics(user: UserRow, today: date | None = None) -> UserMetrics:
    """Derive engagement metrics from a single user row.

    Args:
        user: A UserRow with registration and login data.
        today: Reference date for age/recency calculations (defaults to
               today in UTC).

    Returns:
        UserMetrics with the computed values.
    """
    if today is None:
        today = datetime.now(UTC).date()

    created_date = (
        user.created_at.date() if isinstance(user.created_at, datetime) else user.created_at
    )
    days_since = (today - created_date).days

    if user.last_login_at is not None:
        login_date = (
            user.last_login_at.date()
            if isinstance(user.last_login_at, datetime)
            else user.last_login_at
        )
        distinct_active_days = 1
        weekly_active = (today - login_date).days <= 7
    else:
        distinct_active_days = 0
        weekly_active = False

    return UserMetrics(
        user_id=user.user_id,
        email=user.email,
        days_since_registration=days_since,
        distinct_active_days=distinct_active_days,
        weekly_active=weekly_active,
        score_requests=0,  # No request-log table available yet
    )


def summarize(metrics: list[UserMetrics]) -> dict[str, float]:
    """Compute aggregate engagement stats.

    Returns:
        dict with WAU_pct, median_sessions, and 30day_churn_pct.
    """
    if not metrics:
        return {"WAU_pct": 0.0, "median_sessions": 0.0, "30day_churn_pct": 0.0}

    wau_count = sum(1 for m in metrics if m.weekly_active)
    wau_pct = round(100 * wau_count / len(metrics), 1)

    median_sessions = float(statistics.median(m.distinct_active_days for m in metrics))

    # Churn: registered >30 days ago AND no login in last 30 days
    eligible = [m for m in metrics if m.days_since_registration > 30]
    if eligible:
        churned = sum(1 for m in eligible if m.distinct_active_days == 0 or not m.weekly_active)
        churn_pct = round(100 * churned / len(eligible), 1)
    else:
        churn_pct = 0.0

    return {
        "WAU_pct": wau_pct,
        "median_sessions": median_sessions,
        "30day_churn_pct": churn_pct,
    }


def write_csv(metrics: list[UserMetrics], path: str = "/tmp/retention-audit.csv") -> str:
    """Write one-row-per-user CSV to *path*. Returns the path written."""
    fieldnames = [
        "user_id",
        "email",
        "days_since_registration",
        "distinct_active_days",
        "weekly_active",
        "score_requests",
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for m in metrics:
            writer.writerow(
                {
                    "user_id": m.user_id,
                    "email": m.email,
                    "days_since_registration": m.days_since_registration,
                    "distinct_active_days": m.distinct_active_days,
                    "weekly_active": m.weekly_active,
                    "score_requests": m.score_requests,
                }
            )
    return path


# ---------------------------------------------------------------------------
# DB layer
# ---------------------------------------------------------------------------

_DEFAULT_DSN = "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest"


def _get_dsn() -> str:
    dsn = os.environ.get("MARGIN_DATABASE_URL", _DEFAULT_DSN)
    # Ensure async driver prefix for asyncpg
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return dsn


async def _fetch_users_async(cutoff: date) -> list[UserRow]:
    engine = create_async_engine(_get_dsn())
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, email, created_at, last_login_at "
                "FROM users "
                "WHERE created_at < :cutoff "
                "ORDER BY id"
            ),
            {"cutoff": cutoff},
        )
        rows = result.fetchall()
    await engine.dispose()
    return [
        UserRow(
            user_id=r[0],
            email=r[1],
            created_at=r[2],
            last_login_at=r[3],
        )
        for r in rows
    ]


def fetch_users(cutoff: date | None = None) -> list[UserRow]:
    """Load users registered before *cutoff* from PostgreSQL."""
    if cutoff is None:
        cutoff = date(2026, 4, 1)
    return asyncio.run(_fetch_users_async(cutoff))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("Retention audit -- querying users registered before 2026-04-01 ...")

    users = fetch_users()
    if not users:
        print("No qualifying users found.")
        sys.exit(0)

    today = datetime.now(UTC).date()
    metrics = [compute_metrics(u, today=today) for u in users]

    csv_path = write_csv(metrics)
    summary = summarize(metrics)

    print(f"Wrote {len(metrics)} rows to {csv_path}")
    print(
        f"WAU_pct={summary['WAU_pct']}%  "
        f"median_sessions={summary['median_sessions']}  "
        f"30day_churn_pct={summary['30day_churn_pct']}%"
    )
    print(
        "\nNote: distinct_active_days is limited to 0/1 (only last_login_at "
        "available). Richer session data requires PostHog API integration."
    )


if __name__ == "__main__":
    main()
