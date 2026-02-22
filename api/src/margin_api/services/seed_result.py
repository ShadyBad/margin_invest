"""Result type for seed operations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SeedResult:
    """Rich result from seeding a single ticker."""

    status: str  # "ok", "partial", "failed", "foreign", "skipped"
    categories_succeeded: list[str] = field(default_factory=list)
    categories_failed: list[str] = field(default_factory=list)
    error_message: str | None = None
    provider_used: str = "yfinance"

    @property
    def is_success(self) -> bool:
        return self.status in ("ok", "partial")

    @property
    def data_categories_present(self) -> dict[str, bool]:
        """Category presence map for storage."""
        categories: dict[str, bool] = {}
        for cat in self.categories_succeeded:
            categories[cat] = True
        for cat in self.categories_failed:
            categories[cat] = False
        return categories
