interface PageHeaderProps {
  category: string
  title: string
  description: string
}

export function PageHeader({ category, title, description }: PageHeaderProps) {
  return (
    <header className="mb-16">
      <div className="flex items-center gap-2 mb-4">
        <span
          className="inline-block w-1.5 h-1.5 rounded-full bg-accent"
          aria-hidden="true"
        />
        <span className="text-mono-label text-text-secondary">{category}</span>
      </div>
      <h1 className="text-display-2 text-text-primary mb-4">{title}</h1>
      <p className="text-body text-text-secondary max-w-2xl">{description}</p>
    </header>
  )
}
