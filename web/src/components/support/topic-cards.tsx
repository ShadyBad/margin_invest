import type { FaqCategory } from "./support-data"

const icons: Record<FaqCategory["icon"], React.ReactNode> = {
  shield: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M12 3L4 7V12C4 16.4 7.4 20.5 12 21.5C16.6 20.5 20 16.4 20 12V7L12 3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  chart: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M8 17V10M12 17V7M16 17V13M4 21H20"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  card: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 10H21" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  fingerprint: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M12 10V14M8 12C8 9.8 9.8 8 12 8S16 9.8 16 12M5 12C5 8.1 8.1 5 12 5S19 8.1 19 12M12 18C9.2 18 7 15.8 7 13M17 13C17 15.8 14.8 18 12 18"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
}

export function TopicCards({ categories }: { categories: FaqCategory[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {categories.map((category) => (
        <a
          key={category.id}
          href={`#faq-${category.id}`}
          className="p-5 border border-border-primary rounded-lg bg-bg-elevated hover:border-accent/40 transition-colors group"
        >
          <div className="mb-3">{icons[category.icon]}</div>
          <h3 className="text-[15px] font-semibold text-text-primary mb-1 group-hover:text-accent transition-colors">
            {category.title}
          </h3>
          <p className="text-[13px] text-text-tertiary leading-relaxed">
            {category.description}
          </p>
        </a>
      ))}
    </div>
  )
}
