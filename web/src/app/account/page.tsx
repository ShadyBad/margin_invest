import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { AccountPageClient } from "@/components/account/account-page-client"

export default async function AccountPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <AccountPageClient />
    </AppShell>
  )
}
