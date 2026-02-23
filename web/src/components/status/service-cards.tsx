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
