"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

export interface SidebarProps {
  expanded: boolean
  onToggle: () => void
}

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

interface NavGroup {
  title: string
  items: NavItem[]
}

/* ---------- Inline SVG icons (no icon library) ---------- */

function IconGrid() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function IconStar() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.27 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z" />
    </svg>
  )
}

function IconSearch() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="11" cy="11" r="7" />
      <path strokeLinecap="round" d="M20 20l-4.35-4.35" />
    </svg>
  )
}

function IconTrending() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2v20M17 5H9.5a3.5 3.5 0 100 7h5a3.5 3.5 0 110 7H6" />
    </svg>
  )
}

function IconChart() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="3" y="12" width="4" height="9" rx="1" />
      <rect x="10" y="6" width="4" height="15" rx="1" />
      <rect x="17" y="3" width="4" height="18" rx="1" />
    </svg>
  )
}

function IconBook() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  )
}

function IconCompass() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <circle cx="12" cy="12" r="9" />
      <polygon points="16.24,7.76 14.12,14.12 7.76,16.24 9.88,9.88" fill="currentColor" opacity="0.5" />
    </svg>
  )
}

function IconPulse() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2 12h4l3-9 4 18 3-9h6" />
    </svg>
  )
}

/* ---------- Navigation data ---------- */

const navGroups: NavGroup[] = [
  {
    title: "CORE",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: <IconGrid /> },
      { href: "/watchlist", label: "Watchlist", icon: <IconStar /> },
      { href: "/search", label: "Search", icon: <IconSearch /> },
    ],
  },
  {
    title: "TOOLS",
    items: [
      { href: "/smart-money", label: "Smart Money", icon: <IconTrending /> },
      { href: "/backtesting", label: "Backtesting", icon: <IconChart /> },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { href: "/methodology", label: "Methodology", icon: <IconBook /> },
      { href: "/guides", label: "Guides", icon: <IconCompass /> },
      { href: "/status", label: "Status", icon: <IconPulse /> },
    ],
  },
]

export function Sidebar({ expanded, onToggle }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      data-testid="sidebar"
      className="fixed top-14 left-0 bottom-0 z-40 flex flex-col bg-bg-primary border-r border-border-subtle transition-all duration-300 ease-in-out"
      style={{ width: expanded ? 240 : 64 }}
    >
      {/* Navigation groups */}
      <nav className="flex-1 overflow-y-auto py-4 px-2" aria-label="Sidebar navigation">
        {navGroups.map((group) => (
          <div key={group.title} className="mb-4">
            {expanded && (
              <span className="text-mono-label text-text-tertiary px-3 mb-1 block">
                {group.title}
              </span>
            )}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href || pathname.startsWith(item.href + "/")
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={expanded ? undefined : item.label}
                    className={`
                      relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm
                      transition-colors duration-150
                      ${isActive
                        ? "bg-accent/10 text-text-primary"
                        : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
                      }
                    `}
                  >
                    {/* Active indicator bar */}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r" />
                    )}
                    {item.icon}
                    {expanded && <span>{item.label}</span>}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-border-subtle p-3 flex flex-col gap-2">
        {expanded ? (
          <>
            <div className="flex items-center justify-between px-1">
              <span className="text-mono-label text-text-tertiary">Engine</span>
              <span className="text-mono-label text-text-secondary">v4.2</span>
            </div>
            <div className="flex items-center justify-between px-1">
              <span className="text-mono-label text-text-tertiary">Plan</span>
              <span className="inline-flex items-center rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent uppercase tracking-wider">
                Analyst
              </span>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <span className="text-[9px] text-text-tertiary font-mono">v4.2</span>
          </div>
        )}
      </div>

      {/* Collapse toggle at the very bottom */}
      <button
        onClick={onToggle}
        className="border-t border-border-subtle p-3 flex items-center justify-center text-text-tertiary hover:text-text-secondary transition-colors"
        aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
      >
        <svg
          className={`h-4 w-4 transition-transform duration-300 ${expanded ? "" : "rotate-180"}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </aside>
  )
}
