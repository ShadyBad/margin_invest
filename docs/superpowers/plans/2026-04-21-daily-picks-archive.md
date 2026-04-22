# Daily Picks Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tamper-evident daily picks archive that publishes conviction-gated scores to a public GitHub repo and Cloudflare R2 bucket after every US market close.

**Architecture:** ARQ cron job inside `margin_api` reads published V4Scores, generates a deterministic JSON snapshot with SHA-256 hash chain, and publishes to GitHub + R2 in parallel. Independent failure handling — each publisher can fail without blocking the other.

**Tech Stack:** Python 3.13, Pydantic v2, httpx (async GitHub API), boto3 (R2 via S3 API), pandas_market_calendars (NYSE holidays), ARQ (cron scheduling), PostHog (alerting)

**Spec:** `docs/superpowers/specs/2026-04-21-daily-picks-archive-design.md`

---

See the design spec for full context. This plan is a companion document with task-by-task implementation steps.

The full plan content was presented inline during the brainstorming session and approved by the user. Refer to the conversation history for complete task details including all code blocks.
