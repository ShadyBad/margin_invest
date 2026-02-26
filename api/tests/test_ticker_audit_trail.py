"""Tests for IngestionTickerStatus audit trail.

The original tests in this file tested the monolithic full_ingest function,
which has been replaced by the batched ingest pipeline (ingest_batch).
Audit trail behavior is now tested in test_ingest_batch.py.
"""
