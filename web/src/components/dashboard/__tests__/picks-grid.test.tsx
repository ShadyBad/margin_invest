import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

vi.mock("@/components/ui", () => ({
  EmptyState: ({ title, description, className }: { title: string; description?: string; className?: string }) => (
    <div className={className}><h3>{title}</h3>{description && <p>{description}</p>}</div>
  ),
  ConvictionBadge: ({ level }: { level: string }) => <span>{level}</span>,
}))

import { PicksGrid } from "../picks-grid"

describe("PicksGrid", () => {
  it("renders purposeful empty state when no picks", () => {
    render(<PicksGrid picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/nothing worth your capital/i)).toBeInTheDocument()
  })

  it("shows elimination stats when universe data provided and no picks", () => {
    render(<PicksGrid picks={[]} totalScored={847} universeSize={2847} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/847/)).toBeInTheDocument()
    expect(screen.getByText(/2,847/)).toBeInTheDocument()
  })
})
