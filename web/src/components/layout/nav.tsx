"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { Avatar } from "@/components/ui/avatar"

const navLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/settings", label: "Settings" },
]

export function Nav() {
  const pathname = usePathname()
  const { data: session } = useSession()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => setMounted(true), [])

  return (
    <nav className="bg-bg-elevated border-b border-border-primary">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="text-accent font-bold text-xl">
            Margin Invest
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  pathname === link.href
                    ? "text-accent"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* User Menu */}
          <div className="hidden md:flex items-center gap-4">
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              aria-label="Toggle theme"
            >
              {mounted ? (theme === "dark" ? "\u2600" : "\u25CF") : "\u00A0"}
            </button>
            {session?.user ? (
              <div className="flex items-center gap-3">
                <Avatar
                  name={session.user.name || session.user.email || ""}
                  avatarUrl={(session as any).avatarUrl}
                  oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
                  size="sm"
                />
                <span className="text-sm text-text-secondary">
                  {session.user.name || session.user.email}
                </span>
                <button
                  onClick={() => signOut()}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="text-sm font-medium text-accent hover:text-accent-hover transition-colors"
              >
                Sign In
              </Link>
            )}
          </div>

          {/* Mobile Hamburger */}
          <button
            className="md:hidden text-text-primary"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border-primary">
          <div className="px-4 py-3 space-y-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`block text-sm font-medium py-2 ${
                  pathname === link.href
                    ? "text-accent"
                    : "text-text-secondary"
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            {session?.user ? (
              <div className="flex items-center gap-3 py-2">
                <Avatar
                  name={session.user.name || session.user.email || ""}
                  avatarUrl={(session as any).avatarUrl}
                  oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
                  size="sm"
                />
                <button
                  onClick={() => signOut()}
                  className="text-sm text-text-secondary"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link href="/login" className="block text-sm text-accent py-2">
                Sign In
              </Link>
            )}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="block w-full text-left text-sm text-text-secondary hover:text-text-primary transition-colors py-2"
              aria-label="Toggle theme"
            >
              {mounted ? (theme === "dark" ? "\u2600 Light mode" : "\u25CF Dark mode") : "\u00A0"}
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
