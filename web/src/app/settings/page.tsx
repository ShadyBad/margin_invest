import { AppShell } from "@/components/layout"
import { AccountSection } from "@/components/settings/account-section"
import { ApiKeysSection } from "@/components/settings/api-keys-section"

export default function SettingsPage() {
  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-text-primary mb-8">Settings</h1>
      <div className="space-y-8">
        <AccountSection />
        <ApiKeysSection />
      </div>
    </AppShell>
  )
}
