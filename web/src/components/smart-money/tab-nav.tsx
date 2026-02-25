"use client"

interface TabNavProps {
  tabs: { id: string; label: string }[]
  activeTab: string
  onChange: (id: string) => void
}

export function TabNav({ tabs, activeTab, onChange }: TabNavProps) {
  return (
    <div className="flex gap-1 border-b border-white/[0.06] mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "text-accent border-b-2 border-accent"
              : "text-text-tertiary hover:text-text-secondary"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
