#!/usr/bin/env bash
# Claude Code PreToolUse hook: runs lint before git commit commands.
# Receives tool input JSON on stdin. Exits 2 to block, 0 to proceed.
set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command from the Bash tool input
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only intercept git commit commands
if ! echo "$COMMAND" | grep -qE '^\s*git\s+commit'; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Auto-fix Python lint
uv run ruff check --fix engine/ api/ 2>/dev/null || true
uv run ruff format engine/ api/ 2>/dev/null || true

# Check if unfixable errors remain
if ! uv run ruff check engine/ api/ 2>/dev/null; then
  echo "Blocked: ruff check found unfixable lint errors. Fix them before committing." >&2
  exit 2
fi

# Auto-fix web lint (if web/ files are staged; subshell preserves cwd)
if git diff --cached --name-only | grep -q '^web/'; then
  (
    cd web
    npx eslint . --fix 2>/dev/null || true
    if ! npx eslint . 2>/dev/null; then
      echo "Blocked: eslint found unfixable errors in web/. Fix them before committing." >&2
      exit 2
    fi
  ) || exit 2
fi

exit 0
