"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { useState } from "react"
import { Avatar } from "@/components/ui/avatar"
import { UsagePill } from "./usage-pill"

const publicLinks = [
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
  { href: "/support", label: "Support" },
]

const appLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/settings", label: "Settings" },
]

function LogoIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
    >
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}

interface FloatingNavProps {
  variant: "public" | "app"
}

export function FloatingNav({ variant }: FloatingNavProps) {
  const pathname = usePathname()
  const { data: session } = useSession()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const links = variant === "public" ? publicLinks : appLinks

  return (
    <nav
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-32px)] max-w-[900px]"
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-between bg-[#111113] dark:bg-[#111113] light:bg-[#FAFAF9] border border-border-subtle rounded-2xl px-6 py-3 shadow-[0_2px_16px_rgba(0,0,0,0.3)]">
        {/* Logo */}
        <Link
          href="/"
          className="text-text-primary opacity-80 hover:opacity-100 transition-opacity duration-200"
          aria-label="Margin Invest home"
        >
          <LogoIcon />
        </Link>

        {/* Desktop center links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-[14px] font-medium tracking-[-0.01em] transition-colors duration-200 ease-out ${
                pathname === link.href
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop right side */}
        <div className="hidden md:flex items-center gap-3">
          {variant === "app" && (
            // TODO: Wire to real usage API endpoint
            <UsagePill used={0} limit={3} />
          )}
          {variant === "public" ? (
            <Link
              href="/dashboard"
              className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
            >
              Dashboard
            </Link>
          ) : session?.user ? (
            <div className="flex items-center gap-3">
              <Avatar
                name={session.user.name || session.user.email || ""}
                avatarUrl={session.avatarUrl}
                oauthAvatarUrl={session.oauthAvatarUrl ?? session.user.image}
                size="sm"
              />
              <button
                onClick={() => signOut()}
                className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
            >
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden text-text-primary"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
          aria-expanded={mobileMenuOpen}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            {mobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2 bg-[#111113] dark:bg-[#111113] border border-border-subtle rounded-2xl px-6 py-4">
          <div className="flex flex-col gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-[14px] font-medium py-3 transition-colors duration-200 ease-out ${
                  pathname === link.href
                    ? "text-text-primary"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-border-subtle">
            {variant === "public" ? (
              <Link
                href="/dashboard"
                className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
                onClick={() => setMobileMenuOpen(false)}
              >
                Dashboard
              </Link>
            ) : session?.user ? (
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Avatar
                    name={session.user.name || session.user.email || ""}
                    avatarUrl={session.avatarUrl}
                    oauthAvatarUrl={session.oauthAvatarUrl ?? session.user.image}
                    size="sm"
                  />
                  <span className="text-[13px] text-text-secondary">
                    {session.user.name || session.user.email}
                  </span>
                </div>
                <button
                  onClick={() => signOut()}
                  className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
