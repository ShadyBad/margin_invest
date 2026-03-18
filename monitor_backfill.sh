#!/usr/bin/env bash
# monitor_backfill.sh — Check bootstrap job progress and year distribution
set -euo pipefail

BASE_URL="https://margininvest-production.up.railway.app/api/v1"
KEY_FILE="/Users/brandon/repos/margin_invest/.admin_key"

if [ ! -f "$KEY_FILE" ]; then
  echo "Write admin key to $KEY_FILE first"
  exit 1
fi

ADMIN_KEY=$(cat "$KEY_FILE")

echo "=== $(date -u '+%Y-%m-%d %H:%M UTC') ==="
echo ""

# Jobs
echo "--- Latest Jobs ---"
jobs=$(wget -q -O - "${BASE_URL}/jobs/latest?limit=8" 2>/dev/null)
python3 -c "
import json
data = json.loads('''$jobs''')
print(f\"{'ID':>5} | {'Type':<28} | {'Status':<10} | {'Progress':>8} | {'Started':<20} | Error\")
print('-' * 110)
for j in data[:8]:
    started = (j['started_at'] or '')[:19]
    err = (j['error_message'] or '')[:50]
    print(f\"{j['id']:>5} | {j['job_type']:<28} | {j['status']:<10} | {j['progress']:>7.0%} | {started:<20} | {err}\")
"

echo ""

# PIT stats
echo "--- Year Distribution (2019+) ---"
quality=$(curl -s -H "X-Admin-Key: $ADMIN_KEY" "${BASE_URL}/admin/pit/data-quality")
python3 -c "
import json
d = json.loads('''$quality''')
print(f\"Total snapshots: {d['total_snapshots']:,}\")
yd = d['year_distribution']
for y in sorted(yd.keys()):
    if int(y) >= 2018:
        c = yd[y]
        bar = '#' * (c // 500)
        print(f'  {y}: {c:>6,}  {bar}')
"
