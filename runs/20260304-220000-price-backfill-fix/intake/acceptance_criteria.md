# Acceptance Criteria

1. [x] Inter-batch delay: configurable pause between yfinance batch downloads (default 1s)
2. [x] Retry logic: failed tickers are collected and retried in smaller batches with exponential backoff
3. [x] Better logging: log counts of successful vs failed tickers per batch; log final summary with total success/fail/retry stats
4. [x] No silent mass failures: if >50% of tickers fail, log an ERROR (not just WARNING) to trigger alerting
5. [x] Existing tests pass unchanged
6. [x] New tests cover retry logic and failure summary
7. [x] Lint passes
