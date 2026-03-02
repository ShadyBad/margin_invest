"use client"

import { useSession } from "next-auth/react"
import { useRef, useState } from "react"
import { Avatar } from "@/components/ui/avatar"

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
  credentials: "Email & Password",
}

export function ProfileSection() {
  const { data: session, update } = useSession()
  const authMethod = session?.authMethod
  const oauthProvider = session?.oauthProvider
  const avatarUrl = session?.avatarUrl ?? null
  const oauthAvatarUrl = session?.oauthAvatarUrl ?? session?.user?.image
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const providerLabel =
    authMethod === "oauth" && oauthProvider
      ? PROVIDER_LABELS[oauthProvider] || oauthProvider
      : PROVIDER_LABELS["credentials"]

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
        throw new Error(data?.detail ?? data?.message ?? "Upload failed")
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
    <section id="profile" className="terminal-card p-6 md:p-8">
      <h2 className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6">Profile</h2>
      {session?.user ? (
        <div className="space-y-4">
          <div className="flex items-center gap-5">
            <Avatar
              name={session.user.name || session.user.email || ""}
              avatarUrl={avatarUrl}
              oauthAvatarUrl={oauthAvatarUrl}
              size="xl"
            />
            <div>
              <div className="text-xl font-semibold text-text-primary">
                {session.user.name || "User"}
              </div>
              <div className="mt-0.5 text-sm text-text-secondary">
                {session.user.email}
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded-full bg-bg-subtle text-text-secondary border border-border-primary">
                {providerLabel}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
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
              {uploading ? "Uploading..." : "Upload photo"}
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
            <p className="text-sm text-bearish">{error}</p>
          )}
        </div>
      ) : (
        <p className="text-text-secondary">Loading profile information...</p>
      )}
    </section>
  )
}
