"use client"

import { useState } from "react"
import { useNavigation } from "@/hooks/use-navigation"
import { NavLogo } from "./nav-logo"
import { NavLinks } from "./nav-links"
import { NavCTA } from "./nav-cta"
import { UserDropdown } from "./user-dropdown"
import { MobileMenu } from "./mobile-menu"
import { TickerSearch } from "./ticker-search"

export function Navbar() {
  const nav = useNavigation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-32px)] max-w-[900px]"
      aria-label="Main navigation"
    >
      <div className="relative flex items-center justify-between rounded-xl px-6 py-3 backdrop-blur-[20px]" style={{ background: "rgba(18, 42, 28, 0.7)", border: "1px solid var(--color-ghost-border)" }}>
        <NavLogo href={nav.logoHref} />

        <div className="hidden md:flex absolute left-1/2 -translate-x-1/2">
          <NavLinks links={nav.links} />
        </div>

        <div className="hidden md:flex items-center gap-3">
          <TickerSearch />
          {nav.cta && <NavCTA cta={nav.cta} />}
          {nav.user && (
            <UserDropdown user={nav.user} />
          )}
        </div>

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

      <MobileMenu
        nav={nav}
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />
    </nav>
  )
}
