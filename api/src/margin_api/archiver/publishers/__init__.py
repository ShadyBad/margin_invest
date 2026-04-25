"""Archive publishers — GitHub and R2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishResult:
    """Result of a single publisher's attempt."""

    publisher: str
    success: bool
    skipped: bool = False
    error: str | None = None
