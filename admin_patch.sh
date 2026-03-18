#!/usr/bin/env bash
# admin_patch.sh — PATCH a job status on production
# Usage: ./admin_patch.sh <ADMIN_KEY> <JOB_ID> <STATUS>
set -euo pipefail

BASE_URL="https://margininvest-production.up.railway.app/api/v1"
ADMIN_KEY="${1:?Usage: admin_patch.sh <ADMIN_KEY> <JOB_ID> <STATUS>}"
JOB_ID="${2:?Usage: admin_patch.sh <ADMIN_KEY> <JOB_ID> <STATUS>}"
STATUS="${3:?Usage: admin_patch.sh <ADMIN_KEY> <JOB_ID> <STATUS>}"

curl -s -X PATCH \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"$STATUS\", \"error_message\": \"Cancelled: zombie job from previous deploy\"}" \
  "${BASE_URL}/admin/jobs/${JOB_ID}/status"
