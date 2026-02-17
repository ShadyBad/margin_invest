"use client"

interface ChapterIndicatorProps {
  chapters: number
  activeChapter: number
  labels?: string[]
  onNavigate?: (index: number) => void
}

export function ChapterIndicator({
  chapters,
  activeChapter,
  labels,
  onNavigate,
}: ChapterIndicatorProps) {
  return (
    <nav
      aria-label="Page chapters"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-3"
    >
      {Array.from({ length: chapters }, (_, i) => (
        <button
          key={i}
          data-chapter-dot
          data-active={i === activeChapter ? "true" : "false"}
          aria-label={labels?.[i] ?? `Chapter ${i + 1}`}
          aria-current={i === activeChapter ? "step" : undefined}
          onClick={() => onNavigate?.(i)}
          className={`w-2 h-2 rounded-full transition-all duration-300 ${
            i === activeChapter
              ? "bg-[var(--color-accent)] scale-125"
              : "bg-[var(--color-text-tertiary)] opacity-40 hover:opacity-70"
          }`}
        />
      ))}
    </nav>
  )
}
