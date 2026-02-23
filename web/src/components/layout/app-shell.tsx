import { Navbar } from "@/components/nav/navbar"
import { MfaEnforcementBanner } from "@/components/banners/mfa-enforcement-banner"
import { ScoreNotificationStack } from "@/components/ScoreNotificationStack"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8">
        <MfaEnforcementBanner />
        {children}
      </main>
      <ScoreNotificationStack />
    </div>
  )
}
