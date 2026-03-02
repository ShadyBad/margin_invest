"use client"

interface AccountPillNavProps {
  sections: string[]
  activeSection: string
  onNavigate?: (section: string) => void
}

export function AccountPillNav({
  sections,
  activeSection,
  onNavigate,
}: AccountPillNavProps) {
  return (
    <nav
      aria-label="Account sections"
      className="sticky top-24"
    >
      <div className="flex flex-col gap-1">
        {sections.map((section) => {
          const isActive = section === activeSection
          return (
            <button
              key={section}
              type="button"
              onClick={() => onNavigate?.(section)}
              className={`text-sm font-medium px-4 py-1.5 rounded-lg transition-colors text-left ${
                isActive
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {section}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
