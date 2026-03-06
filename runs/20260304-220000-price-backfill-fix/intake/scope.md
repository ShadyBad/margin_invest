# Scope: Fix price backfill silent failures

## Summary
The price backfill pipeline silently fails for many valid tickers due to Yahoo Finance rate limiting. The code catches `KeyError` when accessing multi-ticker DataFrame results, logs a warning, and moves on — with no retry, no delay between batches, and no summary alerting.

## In Scope
- Add inter-batch delay to avoid rate limiting
- Retry failed tickers in smaller batches with backoff
- Better logging: distinguish rate-limit vs invalid ticker
- Summary log at end with success/failure counts
- Tests for retry and failure-tracking logic

## Out of Scope
- Switching data providers
- Changing the CLI interface
- Modifying the database schema
- Changing the worker/cron scheduling

## Constraints
- Must remain backward-compatible with existing CLI and worker callers
- Must not break existing tests

## Run ID: 20260304-220000-price-backfill-fix
