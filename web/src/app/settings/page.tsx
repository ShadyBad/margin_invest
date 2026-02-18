import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"

export default async function SettingsPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-text-primary mb-8">Settings</h1>
      <div className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <p className="text-text-secondary">
          Product preferences coming soon.
        </p>
      </div>
    </AppShell>
  )
}
