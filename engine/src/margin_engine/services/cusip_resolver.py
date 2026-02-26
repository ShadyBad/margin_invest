"""CUSIP resolution service — OpenFIGI batch resolution with fuzzy name matching fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
OPENFIGI_BATCH_SIZE = 100


@dataclass
class ResolvedSecurity:
    """Result of resolving a CUSIP to a tradeable security."""

    cusip: str
    ticker: str | None
    figi: str | None
    issuer_name: str
    resolution_method: Literal["openfigi", "name_match", "manual", "unresolved"]


@dataclass
class Holding:
    """A single 13F holding with CUSIP and issuer name."""

    cusip: str
    issuer_name: str


@dataclass
class KnownAsset:
    """An asset already in the system, used for fuzzy name matching."""

    ticker: str
    name: str


class CUSIPResolver:
    """Resolves CUSIPs to tickers via OpenFIGI batch API + fuzzy name matching fallback.

    Usage::

        resolver = CUSIPResolver(openfigi_api_key="your-key")
        results = await resolver.resolve_batch(holdings, known_assets)
        for cusip, resolved in results.items():
            print(resolved.ticker, resolved.resolution_method)
    """

    def __init__(self, openfigi_api_key: str | None = None) -> None:
        self._api_key = openfigi_api_key
        self._cache: dict[str, ResolvedSecurity] = {}

    def resolve_from_cache(self, cusip: str) -> ResolvedSecurity | None:
        """Look up a previously resolved CUSIP from the in-memory cache."""
        return self._cache.get(cusip)

    def seed_cache(self, entries: list[ResolvedSecurity]) -> None:
        """Bulk populate the cache with known resolutions."""
        for entry in entries:
            self._cache[entry.cusip] = entry

    async def resolve_batch(
        self,
        holdings: list[Holding],
        known_assets: list[KnownAsset] | None = None,
    ) -> dict[str, ResolvedSecurity]:
        """Resolve a batch of holdings to securities.

        Resolution order:
        1. Check in-memory cache
        2. Call OpenFIGI batch API for remaining CUSIPs
        3. Fuzzy name match against known_assets for any still unresolved
        4. Cache all results before returning

        Args:
            holdings: List of holdings with CUSIPs to resolve.
            known_assets: Optional list of known assets for fuzzy name matching fallback.

        Returns:
            Dict mapping CUSIP -> ResolvedSecurity for every input holding.
        """
        results: dict[str, ResolvedSecurity] = {}
        unresolved: list[Holding] = []

        # Step 1: Check cache
        for holding in holdings:
            cached = self.resolve_from_cache(holding.cusip)
            if cached is not None:
                results[holding.cusip] = cached
            else:
                unresolved.append(holding)

        if not unresolved:
            return results

        # Step 2: OpenFIGI batch resolution
        openfigi_results = await self._call_openfigi(unresolved)
        still_unresolved: list[Holding] = []

        for holding in unresolved:
            if holding.cusip in openfigi_results:
                results[holding.cusip] = openfigi_results[holding.cusip]
            else:
                still_unresolved.append(holding)

        # Step 3: Fuzzy name match fallback
        for holding in still_unresolved:
            match = self._fuzzy_name_match(holding.issuer_name, known_assets or [])
            if match is not None:
                resolved = ResolvedSecurity(
                    cusip=holding.cusip,
                    ticker=match.ticker,
                    figi=None,
                    issuer_name=holding.issuer_name,
                    resolution_method="name_match",
                )
            else:
                resolved = ResolvedSecurity(
                    cusip=holding.cusip,
                    ticker=None,
                    figi=None,
                    issuer_name=holding.issuer_name,
                    resolution_method="unresolved",
                )
            results[holding.cusip] = resolved

        # Step 4: Cache all new results
        for cusip, resolved in results.items():
            self._cache[cusip] = resolved

        return results

    async def _call_openfigi(self, holdings: list[Holding]) -> dict[str, ResolvedSecurity]:
        """Call the OpenFIGI batch API to resolve CUSIPs.

        Sends requests in batches of OPENFIGI_BATCH_SIZE (100).
        Returns only successfully resolved securities.
        """
        results: dict[str, ResolvedSecurity] = {}

        for i in range(0, len(holdings), OPENFIGI_BATCH_SIZE):
            batch = holdings[i : i + OPENFIGI_BATCH_SIZE]
            payload = [{"idType": "ID_CUSIP", "idValue": h.cusip} for h in batch]

            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["X-OPENFIGI-APIKEY"] = self._api_key

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        OPENFIGI_URL,
                        json=payload,
                        headers=headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    response_data = response.json()

                batch_results = self._parse_openfigi_response(response_data, batch)
                results.update(batch_results)

            except httpx.HTTPError as exc:
                logger.warning(
                    "OpenFIGI API error for batch starting at index %d: %s",
                    i,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error calling OpenFIGI for batch starting at index %d: %s",
                    i,
                    exc,
                )

        return results

    def _parse_openfigi_response(
        self,
        response_data: list[dict],
        batch: list[Holding],
    ) -> dict[str, ResolvedSecurity]:
        """Parse the OpenFIGI response array, matching entries back to holdings.

        Each element in response_data corresponds positionally to the request batch.
        Successful entries have ``{"data": [{"ticker": ..., "figi": ..., "name": ...}]}``.
        Failed/unresolved entries have ``{"warning": "..."}``.
        """
        results: dict[str, ResolvedSecurity] = {}

        for idx, item in enumerate(response_data):
            if idx >= len(batch):
                break

            holding = batch[idx]

            if "warning" in item:
                logger.debug(
                    "OpenFIGI warning for CUSIP %s: %s",
                    holding.cusip,
                    item["warning"],
                )
                continue

            data_list = item.get("data", [])
            if not data_list:
                continue

            # Take the first match
            first = data_list[0]
            ticker = first.get("ticker")
            figi = first.get("figi")
            name = first.get("name", holding.issuer_name)

            results[holding.cusip] = ResolvedSecurity(
                cusip=holding.cusip,
                ticker=ticker,
                figi=figi,
                issuer_name=name,
                resolution_method="openfigi",
            )

        return results

    @staticmethod
    def _fuzzy_name_match(
        issuer_name: str,
        known_assets: list[KnownAsset],
    ) -> KnownAsset | None:
        """Case-insensitive substring match in both directions.

        Checks if the issuer name contains a known asset name or vice versa.
        Returns the first matching KnownAsset, or None.
        """
        if not issuer_name or not known_assets:
            return None

        issuer_lower = issuer_name.lower()

        for asset in known_assets:
            asset_lower = asset.name.lower()

            # Exact match (case-insensitive)
            if issuer_lower == asset_lower:
                return asset

            # issuer_name contains asset name
            if asset_lower in issuer_lower:
                return asset

            # asset name contains issuer_name
            if issuer_lower in asset_lower:
                return asset

        return None
