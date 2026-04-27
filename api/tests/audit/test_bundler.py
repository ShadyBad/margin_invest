from __future__ import annotations

import hashlib

import pandas as pd
from margin_api.audit.bundler import emit_csv_bytes


def test_emit_csv_bytes_deterministic() -> None:
    df = pd.DataFrame({"b": [2, 1], "a": [10.0, 20.0]})
    assert emit_csv_bytes(df) == emit_csv_bytes(df)


def test_emit_csv_bytes_columns_sorted_alphabetically() -> None:
    df = pd.DataFrame({"b": [2], "a": [10.0], "c": ["x"]})
    out = emit_csv_bytes(df)
    assert out.split(b"\n")[0] == b"a,b,c"


def test_emit_csv_bytes_floats_fixed_precision() -> None:
    df = pd.DataFrame({"v": [1.123456789]})
    assert b"1.123457" in emit_csv_bytes(df)


def test_emit_csv_bytes_no_index() -> None:
    df = pd.DataFrame({"v": [1, 2, 3]}, index=["x", "y", "z"])
    out = emit_csv_bytes(df)
    assert out.startswith(b"v\n")


def test_emit_csv_bytes_sha256_stable_on_reorder() -> None:
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"b": [3, 4], "a": [1, 2]})
    h1 = hashlib.sha256(emit_csv_bytes(df1)).hexdigest()
    h2 = hashlib.sha256(emit_csv_bytes(df2)).hexdigest()
    assert h1 == h2
