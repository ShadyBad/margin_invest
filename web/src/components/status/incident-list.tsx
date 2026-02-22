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
