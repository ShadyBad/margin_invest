"use client"

import Link from "next/link"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

export function NavMinimal() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-transparent">
      <div
        className="mx-auto flex items-center justify-between h-16"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        <Link href="/" className="text-text-primary font-bold text-lg tracking-[-0.02em]">
          Margin Invest
        </Link>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-text-secondary hover:text-text-primary transition-colors text-sm w-6 h-6 flex items-center justify-center"
            aria-label="Toggle theme"
          >
            {mounted ? (theme === "dark" ? "\u2600" : "\u25CF") : "\u25CF"}
          </button>
          <Link
            href="/dashboard"
            className="inline-block px-6 py-2 bg-accent text-white font-semibold text-[14px] rounded-[4px] hover:bg-accent-hover transition-colors"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </nav>
  )
}
