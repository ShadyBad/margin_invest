"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import posthog from "posthog-js"
import { useKeyboardNav } from "@/hooks/use-keyboard-nav"

function SearchIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

export function TickerSearch() {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState("")
  const buttonRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  const close = useCallback(() => {
    setIsOpen(false)
    setQuery("")
    buttonRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const ticker = query.trim().toUpperCase()
      if (ticker) {
        posthog.capture("asset_searched", { query: ticker })
        router.push(`/asset/${ticker}`)
        setIsOpen(false)
        setQuery("")
      }
    },
    [query, router]
  )

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const openSearch = useCallback(() => setIsOpen(true), [])

  useKeyboardNav({
    onCmdK: openSearch,
    onEscape: isOpen ? close : undefined,
  })

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        close()
      }
    },
    [close]
  )

  return (
    <>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(true)}
        aria-label="Search ticker"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className="flex items-center gap-1.5 justify-center h-8 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-subtle transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary px-2"
      >
        <SearchIcon />
        <kbd className="hidden md:inline-flex items-center gap-0.5 text-xs text-text-tertiary border border-border-subtle rounded px-1 font-mono leading-relaxed">
          <span className="text-xs">&#8984;</span>K
        </kbd>
      </button>

      {isOpen && (
        <>
          <div
            data-testid="search-backdrop"
            className="fixed inset-0 z-[60] bg-black/20"
            onClick={close}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-label="Ticker search"
            aria-modal="true"
            className="fixed z-[61] top-[7px] left-1/2 w-[min(400px,calc(100vw-48px))] search-overlay-enter"
          >
            <form onSubmit={handleSubmit} className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none">
                <SearchIcon />
              </div>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search any ticker..."
                aria-label="Ticker symbol"
                className="w-full h-11 pl-10 pr-4 text-sm bg-bg-elevated border border-border-subtle rounded-xl text-text-primary placeholder-text-tertiary shadow-[0_4px_24px_rgba(0,0,0,0.2)] focus:outline-none focus:border-accent/40 transition-colors"
              />
            </form>
          </div>
        </>
      )}
    </>
  )
}
