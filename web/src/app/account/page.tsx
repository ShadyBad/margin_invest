import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { ProfileSection } from "@/components/account/profile-section"
import { SecuritySection } from "@/components/account/security-section"
import { BillingSection } from "@/components/account/billing-section"

export default async function AccountPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-text-primary mb-8">Account</h1>
      <div className="space-y-8">
        <ProfileSection />
        <SecuritySection />
        <BillingSection />
      </div>
    </AppShell>
  )
}
