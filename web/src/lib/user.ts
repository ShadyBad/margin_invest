const MAX_DISPLAY_LENGTH = 20

interface DisplayNameUser {
  name?: string | null
  email?: string | null
}

export function getDisplayName(user: DisplayNameUser): string {
  const name = user.name?.trim()
  if (name) return truncate(name)

  const prefix = user.email?.split("@")[0]
  if (prefix) return truncate(prefix)

  return "User"
}

function truncate(value: string): string {
  if (value.length <= MAX_DISPLAY_LENGTH) return value
  return value.slice(0, MAX_DISPLAY_LENGTH) + "\u2026"
}
