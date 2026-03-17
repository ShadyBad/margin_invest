"use client"

import { useSession, signOut } from "next-auth/react"
import { usePathname } from "next/navigation"
import { getDisplayName } from "@/lib/user"

export interface NavLink {
  href: string
  label: string
  isActive: boolean
}

export interface UserDropdownItem {
  label: string
  title?: string
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

const PUBLIC_LINKS: { href: string; label: string }[] = [
  { href: "/login", label: "Dashboard" },
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
  { href: "/#pricing", label: "Pricing" },
]

const APP_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/smart-money", label: "Smart Money" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/guides", label: "Guides" },
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
        primary: { label: "Get Started", href: "/login" },
        secondary: { label: "Sign In", href: "/login" },
      }

  const user: NavigationUser | null = isAuthenticated
    ? {
        name: session!.user?.name || session!.user?.email || "",
        email: session!.user?.email || "",
        avatarUrl: session!.avatarUrl ?? null,
        oauthAvatarUrl: session!.oauthAvatarUrl ?? session!.user?.image ?? null,
        dropdownItems: [
          {
            label: getDisplayName(session!.user!),
            title: session!.user?.name?.trim() || session!.user?.email?.split("@")[0] || "User",
            href: "/account",
            type: "link" as const,
          },
          { label: "", type: "divider" as const },
          { label: "Sign Out", onClick: () => signOut(), type: "action" as const },
        ],
      }
    : null

  return { isAuthenticated, links, cta, user, logoHref: "/" }
}
