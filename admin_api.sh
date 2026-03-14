#!/usr/bin/env bash
# admin_api.sh — Helper to call production admin endpoints
# Usage: ./admin_api.sh <METHOD> <ENDPOINT_PATH>
# Example: ./admin_api.sh GET /admin/pit/stats

set -euo pipefail

BASE_URL="https://margininvest-production.up.railway.app/api/v1"
ADMIN_KEY="${1:?Usage: admin_api.sh <ADMIN_KEY> <METHOD> <ENDPOINT_PATH>}"
METHOD="${2:?Usage: admin_api.sh <ADMIN_KEY> <METHOD> <ENDPOINT_PATH>}"
ENDPOINT="${3:?Usage: admin_api.sh <ADMIN_KEY> <METHOD> <ENDPOINT_PATH>}"

BODY="${4:-}"

if [ -n "$BODY" ]; then
  curl -s -X "$METHOD" \
    -H "X-Admin-Key: $ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "${BASE_URL}${ENDPOINT}"
else
  curl -s -X "$METHOD" \
    -H "X-Admin-Key: $ADMIN_KEY" \
    "${BASE_URL}${ENDPOINT}"
fi
