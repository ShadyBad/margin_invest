"""Audit bundler: deterministic CSV emit + manifest + R2 upload + hash verify."""
from __future__ import annotations

import hashlib
import io

import pandas as pd

CSV_FLOAT_FORMAT = "%.6f"


def emit_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to bytes deterministically.

    Columns sorted alphabetically; floats to 6 decimals; no index; LF terminator.
    """
    sorted_df = df.reindex(columns=sorted(df.columns))
    buf = io.StringIO()
    sorted_df.to_csv(
        buf,
        index=False,
        float_format=CSV_FLOAT_FORMAT,
        lineterminator="\n",
    )
    return buf.getvalue().encode("utf-8")


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
