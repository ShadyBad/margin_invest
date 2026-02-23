import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FaqAccordion } from "../faq-accordion"
import type { FaqCategory } from "../support-data"

const mockCategories: FaqCategory[] = [
  {
    id: "test-cat",
    title: "Test Category",
    icon: "shield",
    description: "Test description",
    items: [
      { question: "First question?", answer: "First answer." },
      { question: "Second question?", answer: "Second answer." },
    ],
  },
  {
    id: "other-cat",
    title: "Other Category",
    icon: "chart",
    description: "Other description",
    items: [{ question: "Other question?", answer: "Other answer." }],
  },
]

describe("FaqAccordion", () => {
  it("renders all category headings", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.getByText("Test Category")).toBeInTheDocument()
    expect(screen.getByText("Other Category")).toBeInTheDocument()
  })

  it("renders all questions", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.getByText("First question?")).toBeInTheDocument()
    expect(screen.getByText("Second question?")).toBeInTheDocument()
    expect(screen.getByText("Other question?")).toBeInTheDocument()
  })

  it("hides answers by default", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
  })

  it("shows answer when question is clicked", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
  })

  it("collapses previous answer in same category when another is clicked", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    await user.click(screen.getByText("Second question?"))
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
    expect(screen.getByText("Second answer.")).toBeInTheDocument()
  })

  it("collapses answer when same question is clicked again", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    await user.click(screen.getByText("First question?"))
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
  })

  it("allows independent open state across categories", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    await user.click(screen.getByText("Other question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    expect(screen.getByText("Other answer.")).toBeInTheDocument()
  })

  it("sets id attributes on category sections for anchor linking", () => {
    const { container } = render(<FaqAccordion categories={mockCategories} />)
    expect(container.querySelector("#faq-test-cat")).toBeInTheDocument()
    expect(container.querySelector("#faq-other-cat")).toBeInTheDocument()
  })
})
