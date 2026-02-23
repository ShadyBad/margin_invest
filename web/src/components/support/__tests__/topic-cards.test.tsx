import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TopicCards } from "../topic-cards"
import type { FaqCategory } from "../support-data"

const mockCategories: FaqCategory[] = [
  {
    id: "account",
    title: "Account & Access",
    icon: "shield",
    description: "Login issues and account settings",
    items: [],
  },
  {
    id: "scores",
    title: "Scores & Data",
    icon: "chart",
    description: "How scores update",
    items: [],
  },
]

describe("TopicCards", () => {
  it("renders all category titles", () => {
    render(<TopicCards categories={mockCategories} />)
    expect(screen.getByText("Account & Access")).toBeInTheDocument()
    expect(screen.getByText("Scores & Data")).toBeInTheDocument()
  })

  it("renders all category descriptions", () => {
    render(<TopicCards categories={mockCategories} />)
    expect(screen.getByText("Login issues and account settings")).toBeInTheDocument()
    expect(screen.getByText("How scores update")).toBeInTheDocument()
  })

  it("renders anchor links to FAQ sections", () => {
    render(<TopicCards categories={mockCategories} />)
    const links = screen.getAllByRole("link")
    expect(links[0]).toHaveAttribute("href", "#faq-account")
    expect(links[1]).toHaveAttribute("href", "#faq-scores")
  })
})
