"use client"

import { forwardRef } from "react"
import Link from "next/link"
import { LogoIcon } from "@/components/ui/logo-icon"

export interface TopBarProps {
  sidebarExpanded: boolean
  onMenuToggle: () => void
}

export const TopBar = forwardRef<HTMLInputElement, TopBarProps>(
  function TopBar({ sidebarExpanded, onMenuToggle }, ref) {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center bg-bg-primary border-b border-border-subtle">
        {/* Left section — matches sidebar width for column alignment */}
        <div
          className={`shrink-0 flex items-center h-full transition-[width] duration-300 ease-in-out border-r border-border-subtle ${
            sidebarExpanded ? "gap-3 px-4" : "justify-center"
          }`}
          style={{ width: sidebarExpanded ? 240 : 64 }}
        >
          <button
            onClick={onMenuToggle}
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
            aria-label="Toggle menu"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          {sidebarExpanded && (
            <Link
              href="/"
              className="flex items-center gap-2 text-text-primary hover:text-accent transition-colors"
              aria-label="Margin Invest home"
            >
              <LogoIcon size={22} />
              <span
                className="font-display opacity-90 select-none"
                style={{ fontSize: '15px' }}
              >
                Margin Invest
              </span>
            </Link>
          )}
        </div>

        {/* Content section — search + actions */}
        <div className="flex-1 flex items-center justify-between px-4 min-w-0">
          {/* Search */}
          <div className="flex-1 max-w-md mr-4">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <circle cx="11" cy="11" r="7" />
                <path strokeLinecap="round" d="M20 20l-4.35-4.35" />
              </svg>
              <input
                ref={ref}
                type="text"
                placeholder="Search any ticker..."
                className="w-full h-9 pl-9 pr-14 bg-bg-elevated border border-border-subtle rounded-lg text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-colors"
                readOnly
              />
              <kbd className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 rounded border border-border-subtle bg-bg-primary px-1.5 py-0.5 text-[10px] text-text-tertiary font-mono">
                <span className="text-[11px]">&#8984;</span>K
              </kbd>
            </div>
          </div>

          {/* Right: help, settings, avatar */}
          <div className="flex items-center gap-1 shrink-0">
            <Link
              href="/support"
              className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors cursor-pointer"
              aria-label="Help"
            >
              <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <circle cx="12" cy="12" r="9" />
                <path strokeLinecap="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
                <circle cx="12" cy="17" r="0.5" fill="currentColor" />
              </svg>
            </Link>

            <Link
              href="/settings"
              className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors cursor-pointer"
              aria-label="Settings"
            >
              <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
              </svg>
            </Link>

            <Link
              href="/account"
              className="ml-1 h-8 w-8 rounded-full bg-accent/20 flex items-center justify-center text-xs font-semibold text-accent select-none cursor-pointer hover:bg-accent/30 transition-colors"
              aria-label="Account"
            >
              MI
            </Link>
          </div>
        </div>
      </header>
    )
  }
)
