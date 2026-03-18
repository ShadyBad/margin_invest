#!/usr/bin/env bash
# cancel_job.sh — Cancel a zombie job by ID
set -euo pipefail

JOB_ID="${1:?Usage: cancel_job.sh <JOB_ID> [error_message]}"
ERROR_MSG="${2:-Zombie job — cancelled manually}"

BASE_URL="https://margininvest-production.up.railway.app/api/v1"
KEY_FILE="/Users/brandon/repos/margin_invest/.admin_key"

if [ ! -f "$KEY_FILE" ]; then
  echo "Write admin key to $KEY_FILE first"
  exit 1
fi

ADMIN_KEY=$(cat "$KEY_FILE")

curl -s -X PATCH \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"cancelled\",\"error_message\":\"$ERROR_MSG\"}" \
  "${BASE_URL}/admin/jobs/${JOB_ID}/status" | python3 -m json.tool
