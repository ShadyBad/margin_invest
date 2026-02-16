"use client"

import { useSession } from "next-auth/react"
import { useRef, useState } from "react"
import { Avatar } from "@/components/ui/avatar"

export function AccountSection() {
  const { data: session, update } = useSession()
  const authMethod = (session as any)?.authMethod
  const avatarUrl = (session as any)?.avatarUrl as string | null
  const oauthAvatarUrl = (session as any)?.oauthAvatarUrl ?? session?.user?.image
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await fetch("/api/v1/users/me/avatar", {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || "Upload failed")
      }

      await update()
      window.location.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function handleRemove() {
    setError(null)
    try {
      const res = await fetch("/api/v1/users/me/avatar", {
        method: "DELETE",
      })
      if (!res.ok) throw new Error("Delete failed")
      await update()
      window.location.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed")
    }
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Account</h2>
      {session?.user ? (
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <Avatar
              name={session.user.name || session.user.email || ""}
              avatarUrl={avatarUrl}
              oauthAvatarUrl={oauthAvatarUrl}
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

          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="text-sm text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload Avatar"}
            </button>
            {avatarUrl && (
              <button
                onClick={handleRemove}
                className="text-sm text-text-secondary hover:text-red-400 transition-colors"
              >
                Remove
              </button>
            )}
          </div>
          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

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
