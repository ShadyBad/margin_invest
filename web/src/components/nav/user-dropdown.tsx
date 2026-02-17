"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { Avatar } from "@/components/ui/avatar"
import type { NavigationUser } from "@/hooks/use-navigation"

interface UserDropdownProps {
  user: NavigationUser
}

export function UserDropdown({ user }: UserDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }

    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleEscape)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleEscape)
    }
  }, [isOpen])

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center"
      >
        <Avatar
          name={user.name}
          avatarUrl={user.avatarUrl}
          oauthAvatarUrl={user.oauthAvatarUrl}
          size="sm"
        />
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-48 bg-[#111113] border border-border-subtle rounded-xl py-1 shadow-[0_4px_24px_rgba(0,0,0,0.4)] animate-in fade-in zoom-in-95 duration-150 ease-out"
        >
          {user.dropdownItems.map((item, i) => {
            if (item.type === "divider") {
              return (
                <div
                  key={`divider-${i}`}
                  role="separator"
                  className="my-1 border-t border-border-subtle"
                />
              )
            }

            if (item.type === "link" && item.href) {
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  role="menuitem"
                  className="block px-4 py-2 text-[13px] text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors duration-150"
                  onClick={() => setIsOpen(false)}
                >
                  {item.label}
                </Link>
              )
            }

            return (
              <button
                key={item.label}
                role="menuitem"
                className={`block w-full text-left px-4 py-2 text-[13px] transition-colors duration-150 ${
                  item.label === "Sign Out"
                    ? "text-red-400 hover:text-red-300 hover:bg-bg-elevated"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
                }`}
                onClick={() => {
                  item.onClick?.()
                  setIsOpen(false)
                }}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
