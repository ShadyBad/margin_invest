# Status Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/status` page that shows real-time service health from the backend `/health` endpoint, merged with manual incident updates from a JSON file, with 30-second auto-refresh.

**Architecture:** Next.js API route proxies backend `/health` and merges incidents from a JSON file. The page uses a client component wrapper for polling. Components: StatusBanner (hero), ServiceCards, ActiveIncidents, IncidentHistory. Data types and incident data are separate files.

**Tech Stack:** Next.js 15, React, Tailwind CSS (existing design tokens), Vitest + Testing Library

**Design doc:** `docs/plans/2026-02-22-status-page-design.md`

---

### Task 1: Create status types and incidents data file

**Files:**
- Create: `web/src/components/status/status-types.ts`
- Create: `web/src/data/incidents.json`

**Step 1: Create the types file**

```ts
export type ServiceStatus = "operational" | "degraded" | "outage" | "unknown"
export type OverallStatus = "operational" | "degraded" | "outage"
export type IncidentStatus = "investigating" | "identified" | "monitoring" | "resolved"
export type IncidentSeverity = "minor" | "major" | "maintenance"

export interface ServiceInfo {
  name: string
  status: ServiceStatus
  description: string
}

export interface IncidentUpdate {
  message: string
  timestamp: string
}

export interface Incident {
  id: string
  title: string
  status: IncidentStatus
  severity: IncidentSeverity
  createdAt: string
  resolvedAt: string | null
  updates: IncidentUpdate[]
}

export interface StatusResponse {
  status: OverallStatus
  services: {
    api: ServiceStatus
    database: ServiceStatus
    scoring: ServiceStatus
  }
  version: string
  incidents: Incident[]
}
```

**Step 2: Create the incidents JSON file**

Create `web/src/data/incidents.json` with an empty array (no active incidents to start):

```json
[]
```

**Step 3: Commit**

```bash
git add web/src/components/status/status-types.ts web/src/data/incidents.json
git commit -m "feat(web): add status page types and incidents data file"
```

---

### Task 2: Create the status API route with tests

**Files:**
- Create: `web/src/app/api/v1/status/route.ts`
- Create: `web/src/app/api/v1/status/__tests__/route.test.ts`

**Step 1: Write the failing tests**

```ts
import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock the incidents JSON import
vi.mock("@/data/incidents.json", () => ({
  default: [
    {
      id: "test-incident",
      title: "Test incident",
      status: "investigating",
      severity: "minor",
      createdAt: "2026-02-22T10:00:00Z",
      resolvedAt: null,
      updates: [{ message: "Investigating the issue.", timestamp: "2026-02-22T10:00:00Z" }],
    },
  ],
}))

// Must import after mock
import { GET } from "../route"

describe("GET /api/v1/status", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    vi.restoreAllMocks()
  })

  it("returns operational status when backend is healthy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.services.api).toBe("operational")
    expect(data.services.database).toBe("operational")
    expect(data.services.scoring).toBe("operational")
    expect(data.version).toBe("0.1.0")
  })

  it("returns degraded when backend reports degraded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ version: "0.1.0", database: "ok", redis: "error", status: "degraded" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.services.scoring).toBe("outage")
    expect(data.status).toBe("outage")
  })

  it("returns unknown when backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Connection refused")))

    const response = await GET()
    const data = await response.json()

    expect(data.services.api).toBe("unknown")
    expect(data.services.database).toBe("unknown")
    expect(data.services.scoring).toBe("unknown")
    expect(data.status).toBe("degraded")
  })

  it("includes incidents from the JSON file", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.incidents).toHaveLength(1)
    expect(data.incidents[0].id).toBe("test-incident")
  })

  it("factors active incidents into overall status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    // Active minor incident should make overall status degraded even if services are ok
    expect(data.status).toBe("degraded")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/app/api/v1/status/__tests__/route.test.ts`
Expected: FAIL — module not found

**Step 3: Implement the API route**

```ts
import { NextResponse } from "next/server"
import type { StatusResponse, ServiceStatus, OverallStatus, Incident } from "@/components/status/status-types"
import incidents from "@/data/incidents.json"

const API_URL = process.env.API_URL || "http://localhost:8000"

function mapHealthToServices(health: Record<string, string>): StatusResponse["services"] {
  return {
    api: health.status === "ok" ? "operational" : "outage",
    database: health.database === "ok" ? "operational" : "outage",
    scoring: health.redis === "ok" ? "operational" : "outage",
  }
}

function deriveOverallStatus(
  services: StatusResponse["services"],
  activeIncidents: Incident[]
): OverallStatus {
  const hasMajorIncident = activeIncidents.some(
    (i) => i.status !== "resolved" && i.severity === "major"
  )
  const hasActiveIncident = activeIncidents.some((i) => i.status !== "resolved")
  const serviceValues = Object.values(services) as ServiceStatus[]
  const hasOutage = serviceValues.includes("outage")
  const hasUnknown = serviceValues.includes("unknown")

  if (hasMajorIncident || hasOutage) return "outage"
  if (hasActiveIncident || hasUnknown) return "degraded"
  return "operational"
}

export async function GET() {
  const typedIncidents = incidents as Incident[]
  let services: StatusResponse["services"]
  let version = "unknown"

  try {
    const response = await fetch(`${API_URL}/health`, { cache: "no-store" })
    const health = await response.json()
    services = mapHealthToServices(health)
    version = health.version || "unknown"
  } catch {
    services = { api: "unknown", database: "unknown", scoring: "unknown" }
  }

  const status = deriveOverallStatus(services, typedIncidents)

  const payload: StatusResponse = { status, services, version, incidents: typedIncidents }

  return NextResponse.json(payload, {
    headers: { "Cache-Control": "no-store, max-age=0" },
  })
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/app/api/v1/status/__tests__/route.test.ts`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add web/src/app/api/v1/status/route.ts web/src/app/api/v1/status/__tests__/route.test.ts
git commit -m "feat(web): add status API route with health proxy and incident merge"
```

---

### Task 3: Create StatusBanner component with tests

**Files:**
- Create: `web/src/components/status/status-banner.tsx`
- Create: `web/src/components/status/__tests__/status-banner.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StatusBanner } from "../status-banner"

describe("StatusBanner", () => {
  it("shows All Systems Operational for operational status", () => {
    render(<StatusBanner status="operational" />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
  })

  it("shows Partial Degradation for degraded status", () => {
    render(<StatusBanner status="degraded" />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
  })

  it("shows Major Outage for outage status", () => {
    render(<StatusBanner status="outage" />)
    expect(screen.getByText("Major Outage")).toBeInTheDocument()
  })

  it("applies green styling for operational", () => {
    const { container } = render(<StatusBanner status="operational" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-green")
  })

  it("applies amber styling for degraded", () => {
    const { container } = render(<StatusBanner status="degraded" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-amber")
  })

  it("applies red styling for outage", () => {
    const { container } = render(<StatusBanner status="outage" />)
    const banner = container.firstElementChild
    expect(banner?.className).toContain("border-red")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/status-banner.test.tsx`
Expected: FAIL

**Step 3: Implement StatusBanner**

```tsx
import type { OverallStatus } from "./status-types"

const config: Record<OverallStatus, { label: string; dotColor: string; borderColor: string; bgColor: string }> = {
  operational: {
    label: "All Systems Operational",
    dotColor: "bg-green-500",
    borderColor: "border-green-500/30",
    bgColor: "bg-green-500/5",
  },
  degraded: {
    label: "Partial Degradation",
    dotColor: "bg-amber-500",
    borderColor: "border-amber-500/30",
    bgColor: "bg-amber-500/5",
  },
  outage: {
    label: "Major Outage",
    dotColor: "bg-red-500",
    borderColor: "border-red-500/30",
    bgColor: "bg-red-500/5",
  },
}

export function StatusBanner({ status }: { status: OverallStatus }) {
  const { label, dotColor, borderColor, bgColor } = config[status]
  return (
    <div className={`flex items-center justify-center gap-3 px-6 py-4 rounded-lg border ${borderColor} ${bgColor}`}>
      <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
      <span className="text-[15px] font-semibold text-text-primary">{label}</span>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/status-banner.test.tsx`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/status/status-banner.tsx web/src/components/status/__tests__/status-banner.test.tsx
git commit -m "feat(web): add StatusBanner component with tests"
```

---

### Task 4: Create ServiceCards component with tests

**Files:**
- Create: `web/src/components/status/service-cards.tsx`
- Create: `web/src/components/status/__tests__/service-cards.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ServiceCards } from "../service-cards"
import type { ServiceInfo } from "../status-types"

const mockServices: ServiceInfo[] = [
  { name: "API", status: "operational", description: "Platform availability" },
  { name: "Database", status: "outage", description: "Data storage" },
  { name: "Scoring Engine", status: "unknown", description: "Score computation" },
]

describe("ServiceCards", () => {
  it("renders all service names", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Database")).toBeInTheDocument()
    expect(screen.getByText("Scoring Engine")).toBeInTheDocument()
  })

  it("renders all service descriptions", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("Platform availability")).toBeInTheDocument()
    expect(screen.getByText("Data storage")).toBeInTheDocument()
    expect(screen.getByText("Score computation")).toBeInTheDocument()
  })

  it("renders status labels", () => {
    render(<ServiceCards services={mockServices} />)
    expect(screen.getByText("Operational")).toBeInTheDocument()
    expect(screen.getByText("Outage")).toBeInTheDocument()
    expect(screen.getByText("Unknown")).toBeInTheDocument()
  })

  it("applies green dot for operational", () => {
    const { container } = render(
      <ServiceCards services={[{ name: "API", status: "operational", description: "Test" }]} />
    )
    const dot = container.querySelector("[data-status='operational']")
    expect(dot).toBeInTheDocument()
  })

  it("applies red dot for outage", () => {
    const { container } = render(
      <ServiceCards services={[{ name: "API", status: "outage", description: "Test" }]} />
    )
    const dot = container.querySelector("[data-status='outage']")
    expect(dot).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/service-cards.test.tsx`
Expected: FAIL

**Step 3: Implement ServiceCards**

```tsx
import type { ServiceInfo, ServiceStatus } from "./status-types"

const statusConfig: Record<ServiceStatus, { label: string; dotColor: string }> = {
  operational: { label: "Operational", dotColor: "bg-green-500" },
  degraded: { label: "Degraded", dotColor: "bg-amber-500" },
  outage: { label: "Outage", dotColor: "bg-red-500" },
  unknown: { label: "Unknown", dotColor: "bg-gray-500" },
}

export function ServiceCards({ services }: { services: ServiceInfo[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {services.map((service) => {
        const { label, dotColor } = statusConfig[service.status]
        return (
          <div
            key={service.name}
            className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[15px] font-semibold text-text-primary">{service.name}</h3>
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${dotColor}`}
                  data-status={service.status}
                />
                <span className="text-[12px] text-text-tertiary">{label}</span>
              </div>
            </div>
            <p className="text-[13px] text-text-tertiary">{service.description}</p>
          </div>
        )
      })}
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/service-cards.test.tsx`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/status/service-cards.tsx web/src/components/status/__tests__/service-cards.test.tsx
git commit -m "feat(web): add ServiceCards component with tests"
```

---

### Task 5: Create IncidentList components with tests

**Files:**
- Create: `web/src/components/status/incident-list.tsx`
- Create: `web/src/components/status/__tests__/incident-list.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ActiveIncidents, IncidentHistory } from "../incident-list"
import type { Incident } from "../status-types"

const activeIncident: Incident = {
  id: "test-active",
  title: "API latency spike",
  status: "investigating",
  severity: "minor",
  createdAt: "2026-02-22T10:00:00Z",
  resolvedAt: null,
  updates: [
    { message: "Investigating increased latency.", timestamp: "2026-02-22T10:00:00Z" },
  ],
}

const resolvedIncident: Incident = {
  id: "test-resolved",
  title: "Scheduled maintenance",
  status: "resolved",
  severity: "maintenance",
  createdAt: "2026-02-20T02:00:00Z",
  resolvedAt: "2026-02-20T03:30:00Z",
  updates: [
    { message: "Maintenance complete.", timestamp: "2026-02-20T03:30:00Z" },
    { message: "Maintenance has begun.", timestamp: "2026-02-20T02:00:00Z" },
  ],
}

describe("ActiveIncidents", () => {
  it("renders active incident title", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("API latency spike")).toBeInTheDocument()
  })

  it("renders active incident heading", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("Active Incidents")).toBeInTheDocument()
  })

  it("renders the latest update message", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("Investigating increased latency.")).toBeInTheDocument()
  })

  it("renders status badge", () => {
    render(<ActiveIncidents incidents={[activeIncident]} />)
    expect(screen.getByText("investigating")).toBeInTheDocument()
  })

  it("renders nothing when no active incidents", () => {
    const { container } = render(<ActiveIncidents incidents={[]} />)
    expect(container.firstElementChild).toBeNull()
  })
})

describe("IncidentHistory", () => {
  it("renders resolved incident title", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    expect(screen.getByText("Scheduled maintenance")).toBeInTheDocument()
  })

  it("renders section heading", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    expect(screen.getByText("Past Incidents")).toBeInTheDocument()
  })

  it("shows empty message when no history", () => {
    render(<IncidentHistory incidents={[]} />)
    expect(screen.getByText("No incidents reported in the last 30 days.")).toBeInTheDocument()
  })

  it("renders resolved date", () => {
    render(<IncidentHistory incidents={[resolvedIncident]} />)
    // Should show some formatted date — just check the text exists
    expect(screen.getByText(/Feb/)).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/incident-list.test.tsx`
Expected: FAIL

**Step 3: Implement incident list components**

```tsx
import type { Incident } from "./status-types"

const severityBorder: Record<string, string> = {
  minor: "border-amber-500/30",
  major: "border-red-500/30",
  maintenance: "border-blue-500/30",
}

const severityBg: Record<string, string> = {
  minor: "bg-amber-500/5",
  major: "bg-red-500/5",
  maintenance: "bg-blue-500/5",
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function ActiveIncidents({ incidents }: { incidents: Incident[] }) {
  const active = incidents.filter((i) => i.status !== "resolved")
  if (active.length === 0) return null

  return (
    <section>
      <h2 className="heading-3 text-text-primary mb-4">Active Incidents</h2>
      <div className="space-y-4">
        {active.map((incident) => (
          <div
            key={incident.id}
            className={`p-5 rounded-lg border ${severityBorder[incident.severity] || "border-border-primary"} ${severityBg[incident.severity] || ""}`}
          >
            <div className="flex items-start justify-between gap-4 mb-2">
              <h3 className="text-[15px] font-semibold text-text-primary">{incident.title}</h3>
              <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wide shrink-0">
                {incident.status}
              </span>
            </div>
            {incident.updates.length > 0 && (
              <p className="text-[13px] text-text-secondary leading-relaxed">
                {incident.updates[0].message}
              </p>
            )}
            <p className="text-[12px] text-text-tertiary mt-2">{formatDate(incident.createdAt)}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export function IncidentHistory({ incidents }: { incidents: Incident[] }) {
  const resolved = incidents.filter((i) => i.status === "resolved")

  return (
    <section>
      <h2 className="heading-3 text-text-primary mb-4">Past Incidents</h2>
      {resolved.length === 0 ? (
        <p className="text-[14px] text-text-tertiary">
          No incidents reported in the last 30 days.
        </p>
      ) : (
        <div className="space-y-3">
          {resolved.map((incident) => (
            <div
              key={incident.id}
              className="flex items-center justify-between py-3 border-b border-border-subtle"
            >
              <div>
                <h3 className="text-[14px] font-medium text-text-primary">{incident.title}</h3>
                <p className="text-[12px] text-text-tertiary">{formatDate(incident.createdAt)}</p>
              </div>
              <span className="text-[12px] text-text-tertiary">
                Resolved {incident.resolvedAt ? formatDate(incident.resolvedAt) : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/__tests__/incident-list.test.tsx`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/status/incident-list.tsx web/src/components/status/__tests__/incident-list.test.tsx
git commit -m "feat(web): add ActiveIncidents and IncidentHistory components with tests"
```

---

### Task 6: Create StatusPageClient wrapper and assemble page

**Files:**
- Create: `web/src/components/status/status-page-client.tsx`
- Create: `web/src/components/status/index.ts`
- Create: `web/src/app/status/page.tsx`

**Step 1: Create the client wrapper with polling**

```tsx
"use client"

import { useState, useEffect, useCallback } from "react"
import { StatusBanner } from "./status-banner"
import { ServiceCards } from "./service-cards"
import { ActiveIncidents, IncidentHistory } from "./incident-list"
import type { StatusResponse, ServiceInfo } from "./status-types"

const POLL_INTERVAL = 30_000

function mapToServiceInfos(services: StatusResponse["services"]): ServiceInfo[] {
  return [
    { name: "API", status: services.api, description: "Platform availability and response times" },
    { name: "Database", status: services.database, description: "Data storage and retrieval" },
    { name: "Scoring Engine", status: services.scoring, description: "Score computation and caching" },
  ]
}

export function StatusPageClient({ initial }: { initial: StatusResponse | null }) {
  const [data, setData] = useState<StatusResponse | null>(initial)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/status", { cache: "no-store" })
      if (res.ok) {
        const json: StatusResponse = await res.json()
        setData(json)
        setLastUpdated(new Date())
      }
    } catch {
      // Keep showing last known data
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(refresh, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [refresh])

  if (!data) {
    return (
      <div className="space-y-8">
        <StatusBanner status="degraded" />
        <p className="text-[14px] text-text-tertiary text-center">
          Unable to load status information. Please try again later.
        </p>
      </div>
    )
  }

  const serviceInfos = mapToServiceInfos(data.services)
  const activeIncidents = data.incidents.filter((i) => i.status !== "resolved")
  const resolvedIncidents = data.incidents.filter((i) => i.status === "resolved")

  return (
    <div className="space-y-12">
      <StatusBanner status={data.status} />
      <ServiceCards services={serviceInfos} />
      {activeIncidents.length > 0 && <ActiveIncidents incidents={activeIncidents} />}
      <IncidentHistory incidents={resolvedIncidents} />
      <p className="text-[12px] text-text-tertiary text-center">
        Last updated: {lastUpdated.toLocaleTimeString()} &middot; Refreshes every 30 seconds
      </p>
    </div>
  )
}
```

**Step 2: Create barrel export**

```ts
export { StatusBanner } from "./status-banner"
export { ServiceCards } from "./service-cards"
export { ActiveIncidents, IncidentHistory } from "./incident-list"
export { StatusPageClient } from "./status-page-client"
export type { StatusResponse, ServiceInfo, Incident, OverallStatus, ServiceStatus } from "./status-types"
```

**Step 3: Create the page**

```tsx
import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { StatusPageClient } from "@/components/status"
import type { StatusResponse } from "@/components/status"

export const metadata: Metadata = {
  title: "System Status | Margin Invest",
  description:
    "Real-time status of Margin Invest services — API, database, and scoring engine availability.",
}

const API_URL = process.env.API_URL || "http://localhost:8000"

async function fetchInitialStatus(): Promise<StatusResponse | null> {
  try {
    const { default: incidents } = await import("@/data/incidents.json")
    const response = await fetch(`${API_URL}/health`, { cache: "no-store" })
    const health = await response.json()

    const services: StatusResponse["services"] = {
      api: health.status === "ok" ? "operational" : "outage",
      database: health.database === "ok" ? "operational" : "outage",
      scoring: health.redis === "ok" ? "operational" : "outage",
    }

    const typedIncidents = incidents as StatusResponse["incidents"]
    const hasMajor = typedIncidents.some((i) => i.status !== "resolved" && i.severity === "major")
    const hasActive = typedIncidents.some((i) => i.status !== "resolved")
    const hasOutage = Object.values(services).includes("outage")

    let status: StatusResponse["status"] = "operational"
    if (hasMajor || hasOutage) status = "outage"
    else if (hasActive) status = "degraded"

    return { status, services, version: health.version || "unknown", incidents: typedIncidents }
  } catch {
    return null
  }
}

export default async function StatusPage() {
  const initial = await fetchInitialStatus()

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <div className="text-center mb-12">
            <h1 className="heading-2 text-text-primary mb-3">System Status</h1>
            <p className="body-text text-text-secondary">
              Real-time availability of Margin Invest services.
            </p>
          </div>

          <StatusPageClient initial={initial} />

          <div className="mt-16 pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 4: Verify TypeScript compiles**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit`
Expected: No new errors

**Step 5: Commit**

```bash
git add web/src/components/status/status-page-client.tsx web/src/components/status/index.ts web/src/app/status/page.tsx
git commit -m "feat(web): assemble status page with client polling wrapper"
```

---

### Task 7: Update support page status link

**Files:**
- Modify: `web/src/components/support/contact-section.tsx:29-34`
- Modify: `web/src/components/support/__tests__/contact-section.test.tsx:46-49`

**Step 1: Update the component**

In `web/src/components/support/contact-section.tsx`, change the status page link:

Replace:
```tsx
        <a
          href="https://status.margin-invest.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
        >
          system status
        </a>
```

With:
```tsx
        <a
          href="/status"
          className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
        >
          system status
        </a>
```

**Step 2: Update the test**

In `web/src/components/support/__tests__/contact-section.test.tsx`, change the assertion:

Replace:
```tsx
    expect(statusLink).toHaveAttribute("href", "https://status.margin-invest.com")
```

With:
```tsx
    expect(statusLink).toHaveAttribute("href", "/status")
```

**Step 3: Run the support tests to verify**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/support/`
Expected: All 22 tests PASS

**Step 4: Commit**

```bash
git add web/src/components/support/contact-section.tsx web/src/components/support/__tests__/contact-section.test.tsx
git commit -m "fix(web): update support page status link to internal /status route"
```

---

### Task 8: Add integration test for the status page

**Files:**
- Create: `web/src/components/status/__tests__/status-page.test.tsx`

**Step 1: Write integration tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StatusPageClient } from "../status-page-client"
import type { StatusResponse } from "../status-types"

const operationalResponse: StatusResponse = {
  status: "operational",
  services: { api: "operational", database: "operational", scoring: "operational" },
  version: "0.1.0",
  incidents: [],
}

const degradedResponse: StatusResponse = {
  status: "degraded",
  services: { api: "operational", database: "operational", scoring: "outage" },
  version: "0.1.0",
  incidents: [
    {
      id: "test-1",
      title: "Scoring delays",
      status: "investigating",
      severity: "minor",
      createdAt: "2026-02-22T10:00:00Z",
      resolvedAt: null,
      updates: [{ message: "Looking into it.", timestamp: "2026-02-22T10:00:00Z" }],
    },
  ],
}

const withHistoryResponse: StatusResponse = {
  status: "operational",
  services: { api: "operational", database: "operational", scoring: "operational" },
  version: "0.1.0",
  incidents: [
    {
      id: "past-1",
      title: "Past maintenance",
      status: "resolved",
      severity: "maintenance",
      createdAt: "2026-02-20T02:00:00Z",
      resolvedAt: "2026-02-20T03:00:00Z",
      updates: [{ message: "Done.", timestamp: "2026-02-20T03:00:00Z" }],
    },
  ],
}

describe("StatusPageClient integration", () => {
  it("renders operational state correctly", () => {
    render(<StatusPageClient initial={operationalResponse} />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Database")).toBeInTheDocument()
    expect(screen.getByText("Scoring Engine")).toBeInTheDocument()
    expect(screen.getByText("No incidents reported in the last 30 days.")).toBeInTheDocument()
  })

  it("renders degraded state with active incident", () => {
    render(<StatusPageClient initial={degradedResponse} />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
    expect(screen.getByText("Scoring delays")).toBeInTheDocument()
    expect(screen.getByText("Looking into it.")).toBeInTheDocument()
  })

  it("renders incident history", () => {
    render(<StatusPageClient initial={withHistoryResponse} />)
    expect(screen.getByText("All Systems Operational")).toBeInTheDocument()
    expect(screen.getByText("Past maintenance")).toBeInTheDocument()
  })

  it("renders fallback when initial is null", () => {
    render(<StatusPageClient initial={null} />)
    expect(screen.getByText("Partial Degradation")).toBeInTheDocument()
    expect(screen.getByText(/Unable to load status information/)).toBeInTheDocument()
  })

  it("shows last updated timestamp", () => {
    render(<StatusPageClient initial={operationalResponse} />)
    expect(screen.getByText(/Last updated/)).toBeInTheDocument()
    expect(screen.getByText(/Refreshes every 30 seconds/)).toBeInTheDocument()
  })
})
```

**Step 2: Run the full status test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/status/ src/app/api/v1/status/`
Expected: All tests pass across all status-related files

**Step 3: Commit**

```bash
git add web/src/components/status/__tests__/status-page.test.tsx
git commit -m "test(web): add status page integration tests"
```

---

### Task Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | `status-types.ts` + `incidents.json` — types and data | Type-checked |
| 2 | `api/v1/status/route.ts` — API route proxying /health | 5 tests |
| 3 | `status-banner.tsx` — Hero banner (green/amber/red) | 6 tests |
| 4 | `service-cards.tsx` — 3-column service grid | 5 tests |
| 5 | `incident-list.tsx` — Active incidents + history | 9 tests |
| 6 | `status-page-client.tsx` + `index.ts` + `page.tsx` — Client wrapper + page assembly | Build verification |
| 7 | Update support page link — `/status` instead of external URL | Existing 22 tests |
| 8 | `status-page.test.tsx` — Integration test | 5 tests |
