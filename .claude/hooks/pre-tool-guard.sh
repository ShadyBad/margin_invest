#!/usr/bin/env bash
# pre-tool-guard.sh
# Runs before every tool use. Enforces capabilities.yaml.
# Writes audit events. Blocks disallowed actions.
#
# Claude Code hook: PreToolUse
# Input: JSON on stdin with keys: tool_name, tool_input, session_id

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Resolve current run ID ────────────────────────────────────────────────────
# Look for the most recent run directory
RUN_ID=$(ls -t runs/ 2>/dev/null | head -1 || echo "no-run")
AUDIT_FILE="runs/${RUN_ID}/audit/events.jsonl"

log_audit() {
  local event="$1"
  local details="$2"
  if [ -d "runs/${RUN_ID}/audit" ]; then
    echo "{\"event\": \"${event}\", \"tool\": \"${TOOL_NAME}\", \"session\": \"${SESSION_ID}\", \"details\": ${details}, \"timestamp\": \"${TIMESTAMP}\"}" >> "$AUDIT_FILE"
  fi
}

# ── Secret Redaction Check ────────────────────────────────────────────────────
# If the tool input contains secret patterns, block and alert.

TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // "" | tostring')

check_secrets() {
  local patterns=(
    "sk-[a-zA-Z0-9]+"
    "xoxb-[a-zA-Z0-9-]+"
    "password=[^[:space:]]+"
    "token=[^[:space:]]+"
    "api_key=[^[:space:]]+"
    "aws_secret_access_key=[^[:space:]]+"
  )
  
  for pattern in "${patterns[@]}"; do
    if echo "$TOOL_INPUT" | grep -qiE "$pattern" 2>/dev/null; then
      log_audit "secret_detected_and_blocked" "{\"pattern\": \"${pattern}\"}"
      echo "BLOCKED: Potential secret detected in tool input. Redact before proceeding." >&2
      exit 2  # Exit code 2 = block and show message to Claude
    fi
  done
}

# ── Denylist Check ────────────────────────────────────────────────────────────

check_denylists() {
  if [ "$TOOL_NAME" = "Bash" ]; then
    local command=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
    
    local denied_patterns=(
      "rm -rf /"
      "curl.*| bash"
      "wget.*| bash"
      "sudo "
      "> .env$"
      "> .env\."
      "chmod 777"
    )
    
    for pattern in "${denied_patterns[@]}"; do
      if echo "$command" | grep -qiE "$pattern" 2>/dev/null; then
        log_audit "command_blocked" "{\"command\": \"[REDACTED]\", \"reason\": \"denylist_match\", \"pattern\": \"${pattern}\"}"
        echo "BLOCKED: Command matches denylist pattern. Not permitted by capabilities.yaml." >&2
        exit 2
      fi
    done

    # Block reads of sensitive files
    if echo "$command" | grep -qiE "cat .env$|cat .env\.|cat .*\.pem|cat .*\.key|cat id_rsa" 2>/dev/null; then
      log_audit "sensitive_file_read_blocked" "{\"command\": \"[REDACTED]\"}"
      echo "BLOCKED: Reading secrets/key files is not permitted." >&2
      exit 2
    fi
  fi

  # Block writes to sensitive paths
  if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
    local file_path=$(echo "$INPUT" | jq -r '.tool_input.path // .tool_input.file_path // ""')
    local denied_paths=(".env" "production.config" ".pem" ".key" "id_rsa")
    
    for path in "${denied_paths[@]}"; do
      if echo "$file_path" | grep -qiE "${path}" 2>/dev/null; then
        log_audit "sensitive_write_blocked" "{\"path\": \"${file_path}\"}"
        echo "BLOCKED: Writing to sensitive path not permitted." >&2
        exit 2
      fi
    done
  fi
}

# ── Run Checks ────────────────────────────────────────────────────────────────

check_secrets
check_denylists

# ── Log Allowed Action ────────────────────────────────────────────────────────
log_audit "tool_allowed" "{\"tool\": \"${TOOL_NAME}\"}"

# Exit 0 = allow
exit 0
