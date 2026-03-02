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
      className="sticky top-16 z-10 backdrop-blur-lg bg-bg-primary/80 border-b border-border-subtle py-3 overflow-x-auto -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8"
    >
      <div className="flex gap-1">
        {sections.map((section) => {
          const isActive = section === activeSection
          return (
            <button
              key={section}
              type="button"
              onClick={() => onNavigate?.(section)}
              className={`text-sm font-medium px-4 py-1.5 rounded-full transition-colors whitespace-nowrap ${
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
