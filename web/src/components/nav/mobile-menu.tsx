import Link from "next/link"
import { Avatar } from "@/components/ui/avatar"
import type { NavigationState } from "@/hooks/use-navigation"

interface MobileMenuProps {
  nav: NavigationState
  isOpen: boolean
  onClose: () => void
}

export function MobileMenu({ nav, isOpen, onClose }: MobileMenuProps) {
  if (!isOpen) return null

  return (
    <div className="md:hidden mt-2 bg-[#111113] dark:bg-[#111113] border border-border-subtle rounded-2xl px-6 py-4">
      <div className="flex flex-col gap-1">
        {nav.links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`text-[14px] font-medium py-3 transition-colors duration-200 ease-out ${
              link.isActive
                ? "text-text-primary"
                : "text-text-secondary hover:text-text-primary"
            }`}
            onClick={onClose}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-border-subtle">
        {nav.cta && (
          <div className="flex flex-col gap-2">
            <Link
              href={nav.cta.primary.href}
              className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
              onClick={onClose}
            >
              {nav.cta.primary.label}
            </Link>
          </div>
        )}
        {nav.user && (
          <div className="flex flex-col gap-2 mt-3">
            <div className="flex items-center gap-3 py-2">
              <Avatar
                name={nav.user.name}
                avatarUrl={nav.user.avatarUrl}
                oauthAvatarUrl={nav.user.oauthAvatarUrl}
                size="sm"
              />
              <span className="text-[13px] text-text-secondary">
                {nav.user.name}
              </span>
            </div>
            {nav.user.dropdownItems
              .filter((item) => item.type !== "divider")
              .map((item) =>
                item.type === "link" && item.href ? (
                  <Link
                    key={item.label}
                    href={item.href}
                    className="text-[13px] text-text-secondary hover:text-text-primary py-1 transition-colors duration-200 ease-out"
                    onClick={onClose}
                  >
                    {item.label}
                  </Link>
                ) : (
                  <button
                    key={item.label}
                    className={`text-left text-[13px] py-1 transition-colors duration-200 ease-out ${
                      item.label === "Sign Out"
                        ? "text-red-400 hover:text-red-300"
                        : "text-text-secondary hover:text-text-primary"
                    }`}
                    onClick={() => {
                      item.onClick?.()
                      onClose()
                    }}
                  >
                    {item.label}
                  </button>
                )
              )}
          </div>
        )}
      </div>
    </div>
  )
}
