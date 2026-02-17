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
          className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
        >
          {cta.secondary.label}
        </Link>
      )}
      <Link
        href={cta.primary.href}
        className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
      >
        {cta.primary.label}
      </Link>
    </div>
  )
}
