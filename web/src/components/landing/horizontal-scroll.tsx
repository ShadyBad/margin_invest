"use client"

import { Children, useRef, useState, useEffect, type ReactNode } from "react"

interface HorizontalScrollProps {
  children: ReactNode
  className?: string
}

export function HorizontalScroll({ children, className = "" }: HorizontalScrollProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [progress, setProgress] = useState(0)
  const childArray = Children.toArray(children)
  const count = childArray.length

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    const handleScroll = () => {
      const maxScroll = el.scrollWidth - el.clientWidth
      if (maxScroll > 0) {
        setProgress(el.scrollLeft / maxScroll)
      }
    }

    el.addEventListener("scroll", handleScroll, { passive: true })
    return () => el.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <section className={`relative h-screen ${className}`}>
      <div
        ref={scrollRef}
        data-horizontal-scroll
        className="flex h-full overflow-x-auto overflow-y-hidden snap-x snap-mandatory"
        style={{ scrollbarWidth: "none" }}
      >
        {childArray.map((child, i) => (
          <div
            key={i}
            data-scroll-panel
            className="w-screen h-full flex-shrink-0 snap-center"
          >
            {child}
          </div>
        ))}
      </div>
      {/* Progress indicator */}
      <div
        data-scroll-progress
        className="absolute bottom-8 left-1/2 -translate-x-1/2 h-0.5 rounded-full overflow-hidden"
        style={{ width: `${count * 24}px`, backgroundColor: "var(--color-border-subtle)" }}
      >
        <div
          className="h-full rounded-full transition-transform duration-150"
          style={{
            width: `${100 / count}%`,
            backgroundColor: "var(--color-accent)",
            transform: `translateX(${progress * (count - 1) * 100}%)`,
          }}
        />
      </div>
    </section>
  )
}
