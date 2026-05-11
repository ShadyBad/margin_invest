"""Tests for canonical JSON hasher."""

from __future__ import annotations

from margin_api.archiver.hasher import (
    canonical_json,
    compute_input_data_hash,
    compute_payload_hash,
    sha256_hex,
)


class TestCanonicalJson:
    def test_sorted_keys(self) -> None:
        data = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(data).decode("utf-8")
        assert result == '{"a":2,"m":3,"z":1}'

    def test_no_whitespace(self) -> None:
        data = {"key": "value", "num": 42}
        result = canonical_json(data).decode("utf-8")
        assert " " not in result
        assert "\n" not in result

    def test_utf8_encoding(self) -> None:
        data = {"name": "cafe\u0301"}  # "café" with combining accent
        result = canonical_json(data)
        assert isinstance(result, bytes)
        assert result.decode("utf-8")  # must be valid UTF-8

    def test_deterministic_100_runs(self) -> None:
        data = {"ticker": "AAPL", "score": 87.5, "signal": "strong", "rank": 1}
        first = canonical_json(data)
        for _ in range(99):
            assert canonical_json(data) == first

    def test_nested_sort(self) -> None:
        data = {"outer": {"z": 1, "a": 2}}
        result = canonical_json(data).decode("utf-8")
        # Nested dict keys must also be sorted
        assert result == '{"outer":{"a":2,"z":1}}'

    def test_float_representation(self) -> None:
        data = {"value": 3.14}
        result = canonical_json(data).decode("utf-8")
        assert "3.14" in result

    def test_returns_bytes(self) -> None:
        data = {"x": 1}
        assert isinstance(canonical_json(data), bytes)

    def test_key_order_independence(self) -> None:
        data_a = {"b": 2, "a": 1}
        data_b = {"a": 1, "b": 2}
        assert canonical_json(data_a) == canonical_json(data_b)


class TestSha256Hex:
    def test_known_hash_value(self) -> None:
        # SHA-256 of b"hello" is a well-known value
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert sha256_hex(b"hello") == expected

    def test_empty_bytes_produces_64_char_hex(self) -> None:
        result = sha256_hex(b"")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_returns_lowercase_hex(self) -> None:
        result = sha256_hex(b"test data")
        assert result == result.lower()

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert sha256_hex(b"aaa") != sha256_hex(b"bbb")


class TestComputePayloadHash:
    def test_excludes_payload_hash_field(self) -> None:
        snapshot = {"ticker": "AAPL", "score": 90, "payload_hash": "old_hash_value"}
        result = compute_payload_hash(snapshot)
        # Must equal hash of snapshot without payload_hash
        expected_input = {"ticker": "AAPL", "score": 90}
        from margin_api.archiver.hasher import canonical_json, sha256_hex

        expected = sha256_hex(canonical_json(expected_input))
        assert result == expected

    def test_changing_field_changes_hash(self) -> None:
        snapshot_a = {"ticker": "AAPL", "score": 90}
        snapshot_b = {"ticker": "AAPL", "score": 91}
        assert compute_payload_hash(snapshot_a) != compute_payload_hash(snapshot_b)

    def test_snapshot_without_payload_hash_is_stable(self) -> None:
        snapshot = {"ticker": "MSFT", "signal": "stable"}
        h1 = compute_payload_hash(snapshot)
        h2 = compute_payload_hash(snapshot)
        assert h1 == h2

    def test_payload_hash_field_does_not_affect_result(self) -> None:
        base = {"ticker": "GOOG", "score": 75}
        with_old_hash = {**base, "payload_hash": "aaaa"}
        with_new_hash = {**base, "payload_hash": "bbbb"}
        assert compute_payload_hash(with_old_hash) == compute_payload_hash(with_new_hash)
        assert compute_payload_hash(base) == compute_payload_hash(with_old_hash)


class TestComputeInputDataHash:
    def test_sorted_by_ticker_reversed_input_same_hash(self) -> None:
        rows = [
            {"ticker": "MSFT", "score": 80},
            {"ticker": "AAPL", "score": 90},
            {"ticker": "GOOG", "score": 85},
        ]
        reversed_rows = list(reversed(rows))
        assert compute_input_data_hash(rows) == compute_input_data_hash(reversed_rows)

    def test_different_data_different_hash(self) -> None:
        rows_a = [{"ticker": "AAPL", "score": 90}]
        rows_b = [{"ticker": "AAPL", "score": 91}]
        assert compute_input_data_hash(rows_a) != compute_input_data_hash(rows_b)

    def test_empty_list(self) -> None:
        result = compute_input_data_hash([])
        assert isinstance(result, str)
        assert len(result) == 64

    def test_deterministic_for_same_input(self) -> None:
        rows = [{"ticker": "NVDA", "score": 95}, {"ticker": "AMD", "score": 70}]
        assert compute_input_data_hash(rows) == compute_input_data_hash(rows)

    def test_single_row(self) -> None:
        rows = [{"ticker": "TSLA", "score": 60}]
        result = compute_input_data_hash(rows)
        assert len(result) == 64

    def test_missing_ticker_key_handled(self) -> None:
        # Rows without ticker sort to front (key defaults to "")
        rows = [{"score": 80}, {"ticker": "AAPL", "score": 90}]
        result = compute_input_data_hash(rows)
        assert isinstance(result, str)
        assert len(result) == 64
