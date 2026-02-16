"use client"

import { useSession } from "next-auth/react"
import { Avatar } from "@/components/ui/avatar"

export function AccountSection() {
  const { data: session } = useSession()
  const authMethod = (session as any)?.authMethod

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Account</h2>
      {session?.user ? (
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <Avatar
              name={session.user.name || session.user.email || ""}
              avatarUrl={(session as any).avatarUrl}
              oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
              size="lg"
            />
            <div>
              <div className="text-text-primary font-medium">
                {session.user.name || "User"}
              </div>
              <div className="text-sm text-text-secondary">
                {session.user.email}
              </div>
            </div>
          </div>
          {authMethod === "credentials" && (
            <div className="border-t border-border-primary pt-4">
              <h3 className="text-md font-medium text-text-primary mb-2">Multi-Factor Authentication</h3>
              <p className="text-sm text-text-secondary">MFA is enabled for your account. You can manage your authentication methods below.</p>
            </div>
          )}
        </div>
      ) : (
        <p className="text-text-secondary">Loading account information...</p>
      )}
    </section>
  )
}
