"""Governance config registry, validation, and DB threshold reader.

Provides a typed registry of config keys with their schemas and defaults,
a validation function for checking incoming config values, and a helper
to read current threshold values from the database with registry fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import GovernanceConfig


@dataclass
class ConfigKeySpec:
    """Specification for a governance config key.

    Attributes:
        description: Human-readable description of what this config controls.
        schema: Mapping of field name to (type, min_value, max_value) tuple.
            For float fields, both int and float are accepted at validation time.
        default: Default value dict used when no DB row exists.
    """

    description: str
    schema: dict[str, tuple[type, float, float]]
    default: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CONFIG_REGISTRY: dict[str, ConfigKeySpec] = {
    "circuit_breaker.score_drift": ConfigKeySpec(
        description=(
            "Percentage of conviction changes that triggers the score-drift circuit breaker."
        ),
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 30.0},
    ),
    "circuit_breaker.ingestion_failure": ConfigKeySpec(
        description=(
            "Percentage of ingestion failures that triggers the ingestion-failure circuit breaker."
        ),
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 20.0},
    ),
    "circuit_breaker.ml_regression": ConfigKeySpec(
        description=(
            "Percentage of ML model regression that triggers the ml-regression circuit breaker."
        ),
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 50.0},
    ),
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_config_value(key: str, value: dict) -> list[str]:
    """Validate a config value dict against the registry schema for the given key.

    Args:
        key: A config registry key (e.g. "circuit_breaker.score_drift").
        value: The proposed config value dict to validate.

    Returns:
        A list of error strings. Empty list means the value is valid.
    """
    if key not in CONFIG_REGISTRY:
        return [f"Unknown config key: {key!r}. Must be one of: {sorted(CONFIG_REGISTRY)}"]

    spec = CONFIG_REGISTRY[key]
    errors: list[str] = []

    for field_name, (expected_type, min_val, max_val) in spec.schema.items():
        if field_name not in value:
            errors.append(f"Missing required field: {field_name!r}")
            continue

        field_value = value[field_name]

        # Accept int as a valid substitute for float fields.
        if expected_type is float:
            if not isinstance(field_value, (int, float)) or isinstance(field_value, bool):
                errors.append(
                    f"Field {field_name!r}: expected {expected_type.__name__}, "
                    f"got {type(field_value).__name__!r}"
                )
                continue
        elif not isinstance(field_value, expected_type) or isinstance(field_value, bool):
            errors.append(
                f"Field {field_name!r}: expected {expected_type.__name__}, "
                f"got {type(field_value).__name__!r}"
            )
            continue

        numeric_value = float(field_value)
        if not (min_val <= numeric_value <= max_val):
            errors.append(
                f"Field {field_name!r}: value {field_value} is out of range [{min_val}, {max_val}]"
            )

    return errors


# ---------------------------------------------------------------------------
# DB reader
# ---------------------------------------------------------------------------


async def get_threshold(session: AsyncSession, key: str) -> float:
    """Return the threshold float for a circuit-breaker config key.

    Queries the ``governance_configs`` table for the given key. If a row
    exists, returns its ``config_value["threshold"]``. Otherwise falls back
    to the registry default.

    Args:
        session: SQLAlchemy async session.
        key: A config registry key (e.g. "circuit_breaker.score_drift").

    Returns:
        The current threshold as a float.

    Raises:
        KeyError: If the key is not in the config registry.
    """
    if key not in CONFIG_REGISTRY:
        raise KeyError(f"Unknown config key: {key!r}")

    result = await session.execute(
        select(GovernanceConfig).where(GovernanceConfig.config_key == key)
    )
    row = result.scalar_one_or_none()

    if row is not None and row.config_value is not None:
        return float(row.config_value["threshold"])

    return float(CONFIG_REGISTRY[key].default["threshold"])
