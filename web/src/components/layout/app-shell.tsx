"use client"

import { useState, useCallback, useRef, useSyncExternalStore } from "react"
import { MfaEnforcementBanner } from "@/components/banners/mfa-enforcement-banner"
import { ScoreNotificationStack } from "@/components/ScoreNotificationStack"
import { useKeyboardNav } from "@/hooks/use-keyboard-nav"
import { TopBar } from "./top-bar"
import { Sidebar } from "./sidebar"

const SIDEBAR_KEY = "margin:sidebar-expanded"

function getSnapshot(): boolean {
  try {
    const stored = localStorage.getItem(SIDEBAR_KEY)
    return stored === null ? true : stored === "true"
  } catch {
    return true
  }
}

function getServerSnapshot(): boolean {
  return true
}

function subscribe(callback: () => void): () => void {
  function handleStorage(e: StorageEvent) {
    if (e.key === SIDEBAR_KEY) callback()
  }
  window.addEventListener("storage", handleStorage)
  return () => window.removeEventListener("storage", handleStorage)
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const storedExpanded = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  const [sidebarExpanded, setSidebarExpanded] = useState(storedExpanded)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const handleToggle = useCallback(() => {
    setSidebarExpanded((prev) => {
      const next = !prev
      try {
        localStorage.setItem(SIDEBAR_KEY, String(next))
      } catch {
        // ignore
      }
      return next
    })
  }, [])

  useKeyboardNav({ searchInputRef })

  return (
    <div className="min-h-screen bg-bg-primary">
      <TopBar ref={searchInputRef} onMenuToggle={handleToggle} />
      <Sidebar expanded={sidebarExpanded} onToggle={handleToggle} />
      <main
        className="transition-[margin-left] duration-300 ease-in-out pt-14"
        style={{ marginLeft: sidebarExpanded ? 240 : 64 }}
      >
        <div className="px-4 sm:px-6 lg:px-8 py-6">
          <MfaEnforcementBanner />
          {children}
        </div>
      </main>
      <ScoreNotificationStack />
    </div>
  )
}
