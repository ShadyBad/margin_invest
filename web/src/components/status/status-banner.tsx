import type { OverallStatus } from "./status-types"

const config: Record<
  OverallStatus,
  { label: string; dotColor: string; borderColor: string; bgColor: string }
> = {
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
    <div
      className={`flex items-center justify-center gap-3 px-6 py-4 rounded-lg border ${borderColor} ${bgColor}`}
    >
      <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
      <span className="text-[15px] font-semibold text-text-primary">{label}</span>
    </div>
  )
}
