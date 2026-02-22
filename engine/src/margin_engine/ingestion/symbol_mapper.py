"""Cross-provider symbol translation.

Uses yfinance format as the canonical ticker representation (matches DB storage).
Most symbols are identical across providers — only known exceptions need overrides.

Override format: ``{canonical_ticker: {provider_name: provider_ticker}}``
"""

from __future__ import annotations

from pathlib import Path

import yaml


class SymbolMapper:
    """Translate ticker symbols between canonical (yfinance) format and provider formats.

    Parameters
    ----------
    overrides:
        Mapping of ``{canonical_ticker: {provider_name: provider_ticker}}``.
        When *None*, every lookup is a pass-through.
    """

    def __init__(self, overrides: dict[str, dict[str, str]] | None = None) -> None:
        self._overrides: dict[str, dict[str, str]] = overrides or {}
        # Pre-build reverse index: {provider_name: {provider_ticker: canonical_ticker}}
        self._reverse: dict[str, dict[str, str]] = {}
        for canonical, provider_map in self._overrides.items():
            for provider_name, provider_ticker in provider_map.items():
                self._reverse.setdefault(provider_name, {})[provider_ticker] = canonical

    @classmethod
    def from_yaml(cls, path: Path) -> SymbolMapper:
        """Load overrides from a YAML file.

        Expected format::

            overrides:
              BRK-B:
                polygon: "BRK.B"
        """
        with open(path) as fh:
            data = yaml.safe_load(fh)
        overrides = data.get("overrides") or {}
        return cls(overrides=overrides)

    def to_provider(self, ticker: str, provider_name: str) -> str:
        """Convert a canonical ticker to the provider-specific format.

        Returns the ticker unchanged when no override exists.
        """
        provider_map = self._overrides.get(ticker)
        if provider_map is None:
            return ticker
        return provider_map.get(provider_name, ticker)

    def from_provider(self, ticker: str, provider_name: str) -> str:
        """Convert a provider-specific ticker back to canonical format.

        Returns the ticker unchanged when no reverse mapping exists.
        """
        reverse_map = self._reverse.get(provider_name)
        if reverse_map is None:
            return ticker
        return reverse_map.get(ticker, ticker)
