interface DashboardGreetingProps {
  userName: string
  changesCount: number
  lastUpdated: string
}

function getTimeOfDayGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 17) return "Good afternoon"
  return "Good evening"
}

function formatLastUpdated(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  })
}

function getChangesMessage(count: number): string {
  if (count === 0) return "No score changes since yesterday."
  if (count === 1) return "1 score changed since yesterday."
  return `${count} scores changed since yesterday.`
}

export function DashboardGreeting({ userName, changesCount, lastUpdated }: DashboardGreetingProps) {
  const greeting = getTimeOfDayGreeting()
  const greetingText = userName ? `${greeting}, ${userName}.` : `${greeting}.`

  return (
    <div data-testid="dashboard-greeting">
      <h1 className="text-2xl font-bold text-text-primary">{greetingText}</h1>
      <p className="text-sm text-text-secondary mt-1">{getChangesMessage(changesCount)}</p>
      <p className="text-xs text-text-tertiary mt-1">
        Last updated: {formatLastUpdated(lastUpdated)}
      </p>
    </div>
  )
}
