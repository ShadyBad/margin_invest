"""Margin API — FastAPI service wrapping the scoring engine."""

from __future__ import annotations

__version__ = "0.1.0"

from margin_api.app import create_app
from margin_api.config import Settings, get_settings

__all__ = [
    "__version__",
    "Settings",
    "create_app",
    "get_settings",
]
