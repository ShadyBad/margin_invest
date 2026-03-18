#!/usr/bin/env bash
set -euo pipefail
BASE_URL="https://margininvest-production.up.railway.app/api/v1"
jobs=$(wget -q -O - "${BASE_URL}/jobs/latest?limit=25" 2>/dev/null)
python3 -c "
import json
data = json.loads('''$jobs''')
print(f\"{'ID':>5} | {'Type':<28} | {'Status':<10} | {'Progress':>8} | {'Started':<20} | Error\")
print('-' * 110)
for j in data:
    started = (j['started_at'] or '')[:19]
    err = (j['error_message'] or '')[:50]
    print(f\"{j['id']:>5} | {j['job_type']:<28} | {j['status']:<10} | {j['progress']:>7.0%} | {started:<20} | {err}\")
"
