import { EventTable } from "@/components/admin/event-table"

export default function EventsPage() {
  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-display text-text-primary mb-6">Event Log</h1>
      <EventTable />
    </div>
  )
}
