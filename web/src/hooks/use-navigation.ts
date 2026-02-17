"use client"

import { useSession, signOut } from "next-auth/react"
import { usePathname } from "next/navigation"

export interface NavLink {
  href: string
  label: string
  isActive: boolean
}

export interface UserDropdownItem {
  label: string
  href?: string
  onClick?: () => void
  type: "link" | "action" | "divider"
}

export interface NavigationCTA {
  primary: { label: string; href: string }
  secondary?: { label: string; href: string }
}

export interface NavigationUser {
  name: string
  email: string
  avatarUrl?: string | null
  oauthAvatarUrl?: string | null
  dropdownItems: UserDropdownItem[]
}

export interface NavigationState {
  isAuthenticated: boolean
  links: NavLink[]
  cta: NavigationCTA | null
  user: NavigationUser | null
  logoHref: string
}

const PUBLIC_LINKS = [
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
]

const APP_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/", label: "Mainpage" },
]

export function useNavigation(): NavigationState {
  const { data: session } = useSession()
  const pathname = usePathname()
  const isAuthenticated = !!session?.user

  const rawLinks = isAuthenticated ? APP_LINKS : PUBLIC_LINKS
  const links: NavLink[] = rawLinks.map((link) => ({
    ...link,
    isActive: pathname === link.href,
  }))

  const cta: NavigationCTA | null = isAuthenticated
    ? null
    : {
        primary: { label: "Login", href: "/login" },
        secondary: { label: "Sign Up", href: "/register" },
      }

  const user: NavigationUser | null = isAuthenticated
    ? {
        name: session.user.name || session.user.email || "",
        email: session.user.email || "",
        avatarUrl: session.avatarUrl ?? null,
        oauthAvatarUrl: session.oauthAvatarUrl ?? session.user.image ?? null,
        dropdownItems: [
          { label: "Account", href: "/account", type: "link" as const },
          { label: "Settings", href: "/settings", type: "link" as const },
          { label: "", type: "divider" as const },
          { label: "Sign Out", onClick: () => signOut(), type: "action" as const },
        ],
      }
    : null

  return { isAuthenticated, links, cta, user, logoHref: "/" }
}
