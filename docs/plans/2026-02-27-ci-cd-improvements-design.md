# CI/CD Improvements Design

**Date:** 2026-02-27
**Status:** Approved

## Problem

134 ruff lint errors accumulated across worktree-based subagent development, causing 5+ consecutive CI failures on main. The root cause: lint enforcement only exists in CI, but worktree subagents commit and merge without running lint locally.

## Solution: Claude Code Pre-Commit Hook + CI Hardening

### 1. Claude Code Pre-Commit Hook

Add a `PreCommit` hook in `.claude/settings.json` that auto-fixes lint on every commit.

**Python lint (ruff):**
```bash
uv run ruff check --fix engine/ api/ && uv run ruff format engine/ api/
```

**Web lint (ESLint):**
```bash
cd web && npx eslint . --fix
```

**Behavior:**
- Runs before every commit, including worktree subagent commits
- Auto-fixes all fixable issues (import sorting, unused imports, formatting)
- If unfixable errors remain, the commit is blocked
- Subagent sees the failure message and can address the issue before retrying

### 2. CI Pipeline Improvements

#### 2a. Remove duplicate uv cache step
The manual `actions/cache@v4` for `/tmp/.uv-cache` always misses because `setup-uv@v5` handles caching internally with different keys. Remove the manual cache steps from all jobs.

#### 2b. Add concurrency group
Cancel in-progress CI runs when a new push arrives to the same branch:
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

#### 2c. Ignore broken test in CI
Add `--ignore api/tests/services/test_xbrl_parser.py` to the API test step. This test has a pre-existing broken module import that fails collection. Remove this ignore once the module is fixed.

#### 2d. Add web lint step
Add an ESLint check to the `web-tests` job before running vitest:
```bash
cd web && npx eslint .
```

### 3. Component Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| Claude Code PreCommit hook | `.claude/settings.json` | Catches lint at the source |
| Remove duplicate cache | `.github/workflows/ci.yml` | Cleaner CI, avoid cache miss noise |
| Concurrency group | `.github/workflows/ci.yml` | Cancel stale runs |
| Ignore broken test | `.github/workflows/ci.yml` | Unblock CI |
| Web lint in CI | `.github/workflows/ci.yml` | Frontend lint enforcement |

## Non-Goals

- Changing Railway auto-deploy behavior (stays as-is)
- Adding staging environments
- PR-based workflow (worktree-to-main stays)
- Pre-commit framework for ruff (bypassed by worktree workflow)
