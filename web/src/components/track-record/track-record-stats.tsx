/**
 * TrackRecordStats — Summary statistics for track record page.
 *
 * Shows: Total scores logged | Scoring cycles completed | Days since launch.
 */

interface StatCard {
  value: string | number
  label: string
}

const LAUNCH_DATE = new Date("2026-04-01")

function daysSinceLaunch(): number {
  const now = new Date()
  const diff = now.getTime() - LAUNCH_DATE.getTime()
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)))
}

export function TrackRecordStats() {
  const days = daysSinceLaunch()

  const stats: StatCard[] = [
    { value: "30,540", label: "Total scores logged" },
    { value: "247", label: "Scoring cycles completed" },
    { value: days.toLocaleString(), label: "Days since launch" },
  ]

  return (
    <section className="py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="terminal-card p-5 space-y-2">
              <p className="text-2xl font-mono font-semibold text-accent">{stat.value}</p>
              <p className="text-sm font-medium text-text-primary">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
