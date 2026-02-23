# Status Page Design

**Date**: 2026-02-22
**Status**: Approved

## Overview

Add a `/status` page within the Next.js app that displays real-time service health (from the backend `/health` endpoint) and manual incident updates (from a version-controlled JSON file). Auto-refreshes every 30 seconds.

## Page Structure

```
Navbar
Hero banner (overall status: Operational / Degraded / Outage)
Service cards (3: API, Database, Scoring Engine)
Active incidents (if any)
Incident history (resolved, last 30 days)
Back to Home
```

### Hero Banner

Single-line status indicator derived from both live health checks and active incidents:

- **All Systems Operational** — green accent. Requires: all services "operational" AND no active incidents.
- **Partial Degradation** — amber. Triggered by: any service "degraded" OR active minor/maintenance incidents.
- **Major Outage** — red. Triggered by: any service in "outage" OR active major incident.

### Service Cards

Three cards in a row (stacking on mobile). Each has a service name, colored status dot, and one-line description.

| Service | Mapped from /health | Description |
|---------|-------------------|-------------|
| API | Overall `status` field | Platform availability and response times |
| Database | `database` field | Data storage and retrieval |
| Scoring Engine | `redis` field | Score computation and caching |

Status states per card:
- **Operational** — green dot
- **Degraded** — amber dot
- **Outage** — red dot
- **Unknown** — gray dot (when backend unreachable)

Card styling: `border-border-primary`, `bg-bg-elevated`, `rounded-lg` (consistent with Support page).

### Active Incidents

Displayed between service cards and history. Only shown when unresolved incidents exist. Styled with amber/red border based on severity. Each shows title, status badge, severity, and the most recent update message.

### Incident History

Compact list of resolved incidents from the last 30 days. Each shows title, date, and resolution time. If empty: "No incidents reported in the last 30 days."

## Data Flow

### API Route

**Path**: `web/src/app/api/v1/status/route.ts`

Two responsibilities:
1. Proxy the backend `/health` endpoint (server-side, no CORS)
2. Read `web/src/data/incidents.json` and merge into response

Response shape:

```json
{
  "status": "operational | degraded | outage",
  "services": {
    "api": "operational",
    "database": "operational",
    "scoring": "operational"
  },
  "version": "0.1.0",
  "incidents": []
}
```

**Graceful degradation**: If backend `/health` call fails (timeout, unreachable), the API route returns all services as `"unknown"` and still includes incidents. The page renders an "Unable to reach backend" message rather than crashing.

### Client-Side Refresh

A client wrapper component polls `/api/v1/status` every 30 seconds and updates the UI. No WebSocket complexity.

## Incidents JSON File

**Path**: `web/src/data/incidents.json`

Simple array of incident objects, newest first. Edit and commit/deploy to post or resolve incidents.

```json
[
  {
    "id": "2026-02-20-db-maintenance",
    "title": "Scheduled database maintenance",
    "status": "resolved",
    "severity": "maintenance",
    "createdAt": "2026-02-20T02:00:00Z",
    "resolvedAt": "2026-02-20T03:30:00Z",
    "updates": [
      {
        "message": "Maintenance complete. All systems normal.",
        "timestamp": "2026-02-20T03:30:00Z"
      },
      {
        "message": "Database maintenance has begun. Scoring may be delayed.",
        "timestamp": "2026-02-20T02:00:00Z"
      }
    ]
  }
]
```

### Fields

- `id`: Unique slug (date prefix + short description)
- `title`: Human-readable incident title
- `status`: `"investigating"` | `"identified"` | `"monitoring"` | `"resolved"`
- `severity`: `"minor"` | `"major"` | `"maintenance"`
- `createdAt`: ISO 8601 timestamp
- `resolvedAt`: ISO 8601 timestamp (null if active)
- `updates`: Reverse-chronological array of `{ message, timestamp }` entries

### How Severity Affects Hero Banner

- Any active `"major"` incident: hero shows **Major Outage** (red)
- Any active `"minor"` or `"maintenance"`: hero shows **Partial Degradation** (amber)
- Health check `"degraded"` with no incidents: hero shows **Partial Degradation** (amber)
- Both must be clear for **All Systems Operational** (green)

## Technical Details

- **Route**: `web/src/app/status/page.tsx`
- **API route**: `web/src/app/api/v1/status/route.ts`
- **Components**: `web/src/components/status/` — StatusPage (client wrapper), ServiceCards, ActiveIncidents, IncidentHistory, StatusBanner
- **Data**: `web/src/data/incidents.json`
- **Layout**: `max-w-3xl` container, consistent with Support and Legal pages
- **Styling**: Existing design tokens only
- **Dependencies**: None added
- **Polling**: `setInterval` in client wrapper, 30-second interval

## Side Effects

- Update `ContactSection` (`web/src/components/support/contact-section.tsx`) status link from `https://status.margin-invest.com` to `/status`
- Update `ContactSection` test to expect `/status` instead of `https://status.margin-invest.com`

## Service-to-Health Mapping

The backend `/health` endpoint returns:

```json
{
  "version": "0.1.0",
  "database": "ok | error",
  "redis": "ok | error",
  "status": "ok | degraded"
}
```

Mapping to user-facing services:

| User-facing | Health field | ok → | error → |
|-------------|------------|------|---------|
| API | `status` | operational | outage |
| Database | `database` | operational | outage |
| Scoring Engine | `redis` | operational | outage |
