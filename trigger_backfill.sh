#!/usr/bin/env bash
# trigger_backfill.sh — Trigger historical score backfill on production
set -euo pipefail

BASE_URL="https://margininvest-production.up.railway.app/api/v1"
ADMIN_KEY=$(cat .admin_key)

echo "=== Triggering historical score backfill ==="
curl -s -X POST \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  "${BASE_URL}/admin/historical/backfill" | python3 -m json.tool

echo ""
echo "=== Current historical stats ==="
curl -s \
  -H "X-Admin-Key: $ADMIN_KEY" \
  "${BASE_URL}/admin/historical/stats" | python3 -m json.tool

echo ""
echo "=== Monitor with: ./check_jobs.sh ==="
