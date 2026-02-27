"use client"

import { EventTable } from "@/components/admin/event-table"

export default function EventsPage() {
  const adminKey = process.env.NEXT_PUBLIC_ADMIN_KEY || ""
  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-display text-text-primary mb-6">Event Log</h1>
      <EventTable adminKey={adminKey} />
    </div>
  )
}
