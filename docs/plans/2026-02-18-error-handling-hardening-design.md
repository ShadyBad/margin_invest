# Error Handling Hardening Design

**Date**: 2026-02-18
**Status**: Approved
**Scope**: Fix dashboard 500 error + structured error handling across backend and frontend

## Problem

Clicking any candidate card on the dashboard shows `{"error":"Internal Server Error"}` to the user. The raw JSON leaks because:

1. **Backend**: No global exception handler. Unhandled exceptions in `_score_response_from_row()` or `compute_*` functions produce FastAPI's default `{"detail":"Internal Server Error"}`.
2. **Frontend**: `apiFetch` reads the error response as raw text and passes it directly to `ApiError.message`, which the card renders verbatim.

## Root Cause

The `_score_response_from_row()` function in `scores.py` performs extensive dict manipulation on `score_detail` JSONB without try/except. Any missing key, None value, or unexpected type causes an unhandled exception. The `compute_*` metric functions may also crash on NaN values from yfinance data.

## Design

### 1. Backend: Structured Error Response Model

New file: `api/src/margin_api/schemas/errors.py`

```python
class ErrorResponse(BaseModel):
    error_code: str          # Machine-readable: "INTERNAL_ERROR", "SCORE_NOT_FOUND"
    message: str             # Human-readable: "Unable to retrieve candidate details."
    request_id: str          # UUID for log correlation
    status_code: int         # HTTP status code
```

### 2. Backend: Request ID Middleware

New middleware in `app.py` that:
- Generates UUID4 per request
- Attaches to `request.state.request_id`
- Adds `X-Request-Id` response header

### 3. Backend: Global Exception Handlers

Register in `app.py`:
- `Exception` handler: logs full traceback with request_id, returns `ErrorResponse` with generic message
- `HTTPException` handler: wraps existing 404s etc. in `ErrorResponse` format

### 4. Backend: Root Cause Fix

- Wrap `_score_response_from_row()` JSONB parsing in try/except; fall through to summary-column path on failure
- Add NaN filtering in `compute_*` metric functions
- Wrap `get_metrics` endpoint so it returns nulls for metrics it can't compute rather than crashing

### 5. Frontend: Parse Structured Errors

Modify `apiFetch` in `client.ts`:
- Parse error response as JSON (not raw text)
- Extract `error_code`, `message`, `request_id` from structured response
- Set `ApiError.message` to the friendly `message` field

Extend `ApiError` class with `errorCode` and `requestId` fields.

### 6. Frontend: Card Error State with Retry

Replace bare error text in `stock-card.tsx` with:
- Friendly title: "Unable to load candidate details"
- Subtext: "This data is temporarily unavailable."
- Retry button that clears error and re-fetches
- Console log with request_id for debugging

Change `Promise.all` to `Promise.allSettled` so a metrics failure doesn't block score display.

### 7. Frontend: AssetPanel Error Boundary

New error boundary component wrapping the AssetPanel portal:
- Catches render-time crashes in sub-components
- Shows "Unable to display details" with dismiss button
- Prevents whole dashboard from crashing

## Files Modified

| File | Change |
|------|--------|
| `api/src/margin_api/schemas/errors.py` | New: ErrorResponse model |
| `api/src/margin_api/app.py` | Add RequestIdMiddleware + exception handlers |
| `api/src/margin_api/routes/scores.py` | Wrap _score_response_from_row in try/except |
| `api/src/margin_api/routes/metrics.py` | Defensive guards on compute functions |
| `api/src/margin_api/services/metrics.py` | Filter NaN values in compute_* functions |
| `web/src/lib/api/client.ts` | Parse structured error JSON, extend ApiError |
| `web/src/components/dashboard/stock-card.tsx` | Error state UI + retry + Promise.allSettled |
| `web/src/components/dashboard/panel/asset-panel.tsx` | Wrap in error boundary |

## Acceptance Criteria

- Clicking any candidate card never shows raw JSON
- Backend returns structured `ErrorResponse` for all error status codes
- UI displays friendly error messages with retry option
- No uncaught promise rejections
- Request IDs in error responses match server logs
- Metrics failure doesn't prevent score display
- AssetPanel render crashes are caught by error boundary
