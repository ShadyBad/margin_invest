import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TopicCards, FaqAccordion, ContactSection, faqCategories, contactCards } from "../index"

describe("Support page integration", () => {
  function renderSupportContent() {
    return render(
      <>
        <TopicCards categories={faqCategories} />
        <FaqAccordion categories={faqCategories} />
        <ContactSection cards={contactCards} />
      </>
    )
  }

  it("renders all four topic cards", () => {
    renderSupportContent()
    // Each title appears twice: once in TopicCards (h3) and once in FaqAccordion (h2)
    expect(screen.getAllByText("Account & Access")).toHaveLength(2)
    expect(screen.getAllByText("Scores & Data")).toHaveLength(2)
    expect(screen.getAllByText("Billing & Subscription")).toHaveLength(2)
    expect(screen.getAllByText("Security & Privacy")).toHaveLength(2)

    // Verify the topic card headings specifically (h3)
    const h3s = screen.getAllByRole("heading", { level: 3 })
    const topicCardTitles = h3s
      .map((h) => h.textContent)
      .filter((t) => faqCategories.some((c) => c.title === t))
    expect(topicCardTitles).toEqual([
      "Account & Access",
      "Scores & Data",
      "Billing & Subscription",
      "Security & Privacy",
    ])
  })

  it("renders all FAQ questions from real data", () => {
    renderSupportContent()
    for (const category of faqCategories) {
      for (const item of category.items) {
        expect(screen.getByText(item.question)).toBeInTheDocument()
      }
    }
  })

  it("accordion opens and shows answer from real data", async () => {
    const user = userEvent.setup()
    renderSupportContent()
    await user.click(screen.getByText("I can't log in to my account"))
    expect(screen.getByText(/Check that your email and password are correct/)).toBeInTheDocument()
  })

  it("renders all three contact cards with mailto links", () => {
    renderSupportContent()
    expect(screen.getByText("support@margin-invest.com")).toBeInTheDocument()
    expect(screen.getByText("security@margin-invest.com")).toBeInTheDocument()
    expect(screen.getByText("legal@margin-invest.com")).toBeInTheDocument()
  })

  it("renders status page link", () => {
    renderSupportContent()
    expect(screen.getByRole("link", { name: /system status/i })).toHaveAttribute(
      "href",
      "https://status.margin-invest.com"
    )
  })

  it("topic cards link to correct FAQ sections", () => {
    renderSupportContent()
    const links = screen.getAllByRole("link").filter((l) => l.getAttribute("href")?.startsWith("#"))
    expect(links).toHaveLength(4)
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "#faq-account",
      "#faq-scores",
      "#faq-billing",
      "#faq-security",
    ])
  })
})
