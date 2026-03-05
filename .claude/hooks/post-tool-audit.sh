#!/usr/bin/env bash
# post-tool-audit.sh  
# Runs after every tool use. Writes audit trail. Redacts output.
#
# Claude Code hook: PostToolUse
# Input: JSON on stdin with keys: tool_name, tool_input, tool_response, session_id

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // "null"')

# ── Resolve current run ID ────────────────────────────────────────────────────
RUN_ID=$(ls -t runs/ 2>/dev/null | head -1 || echo "no-run")
AUDIT_DIR="runs/${RUN_ID}/audit"
AUDIT_FILE="${AUDIT_DIR}/events.jsonl"

# Ensure audit dir exists
mkdir -p "$AUDIT_DIR" 2>/dev/null || true

# ── Redact Sensitive Output ────────────────────────────────────────────────────
# Redact secrets from tool response before logging

TOOL_RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // {} | tostring')

redact_output() {
  local content="$1"
  
  # Redact common secret patterns
  content=$(echo "$content" | sed -E 's/sk-[a-zA-Z0-9]+/[REDACTED:api_key]/g')
  content=$(echo "$content" | sed -E 's/xoxb-[a-zA-Z0-9-]+/[REDACTED:slack_token]/g')
  content=$(echo "$content" | sed -E 's/Bearer [a-zA-Z0-9._-]+/Bearer [REDACTED:bearer_token]/g')
  content=$(echo "$content" | sed -E 's/(password|passwd|pwd)=[^[:space:]]+/\1=[REDACTED:password]/gi')
  content=$(echo "$content" | sed -E 's/(token|api_key|secret|apikey)=[^[:space:]]+/\1=[REDACTED:secret]/gi')
  content=$(echo "$content" | sed -E 's/(aws_access_key_id|aws_secret_access_key)=[^[:space:]]+/\1=[REDACTED:aws_key]/gi')
  
  echo "$content"
}

REDACTED_RESPONSE=$(redact_output "$TOOL_RESPONSE")

# ── Write Audit Event ─────────────────────────────────────────────────────────

# Truncate response to avoid huge logs (keep first 500 chars)
TRUNCATED_RESPONSE=$(echo "$REDACTED_RESPONSE" | head -c 500)

jq -cn \
  --arg event "tool_used" \
  --arg tool "$TOOL_NAME" \
  --arg session "$SESSION_ID" \
  --arg run "$RUN_ID" \
  --arg ts "$TIMESTAMP" \
  --argjson exit_code "${EXIT_CODE}" \
  --arg response_preview "$TRUNCATED_RESPONSE" \
  '{
    event: $event,
    tool: $tool,
    session_id: $session,
    run_id: $run,
    exit_code: $exit_code,
    response_preview: $response_preview,
    timestamp: $ts
  }' >> "$AUDIT_FILE" 2>/dev/null || true

# ── Post-commit Gate (block-at-submit strategy) ───────────────────────────────
# If Claude just ran a git commit, check that tests passed first.
# This implements the "block-at-submit" pattern — most reliable hook strategy.

if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
  
  if echo "$COMMAND" | grep -q "git commit"; then
    # Check if pre-commit gate file exists (created by test runner)
    if [ ! -f "/tmp/gsd-tests-passed-${RUN_ID}" ]; then
      # Log the commit attempt without tests
      jq -cn \
        --arg run "$RUN_ID" \
        --arg ts "$TIMESTAMP" \
        '{event: "commit_without_test_gate", run_id: $run, timestamp: $ts, warning: "Tests may not have been verified before commit"}' \
        >> "$AUDIT_FILE" 2>/dev/null || true
    fi
  fi
  
  # If tests just passed, create gate file
  if echo "$COMMAND" | grep -qE "npm test|pytest|cargo test|go test"; then
    if [ "${EXIT_CODE}" = "0" ]; then
      touch "/tmp/gsd-tests-passed-${RUN_ID}" 2>/dev/null || true
    else
      rm -f "/tmp/gsd-tests-passed-${RUN_ID}" 2>/dev/null || true
    fi
  fi
fi

exit 0
