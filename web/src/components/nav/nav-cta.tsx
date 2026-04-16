import Link from "next/link"
import type { NavigationCTA } from "@/hooks/use-navigation"

interface NavCTAProps {
  cta: NavigationCTA
}

export function NavCTA({ cta }: NavCTAProps) {
  return (
    <div className="flex items-center gap-3">
      {cta.secondary && (
        <Link
          href={cta.secondary.href}
          className="text-[13px] transition-colors duration-200 ease-out"
          style={{ color: "var(--color-on-surface-variant)" }}
        >
          {cta.secondary.label}
        </Link>
      )}
      <Link
        href={cta.primary.href}
        className="text-[13px] font-semibold px-4 py-1.5 transition-colors duration-200 ease-out"
        style={{
          background: "var(--color-primary-container)",
          color: "var(--color-on-primary-container)",
          borderRadius: "0.375rem",
        }}
      >
        {cta.primary.label}
      </Link>
    </div>
  )
}
