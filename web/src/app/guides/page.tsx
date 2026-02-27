import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { GuideCategoryTabs } from "@/components/guides/guide-category-tabs"
import { getAllGuides, groupGuidesByCategory } from "@/lib/guides"

export const metadata: Metadata = {
  title: "Guides | Margin Invest",
  description:
    "Learn how Margin Invest scores equities, interpret conviction ratings, and get the most from the platform.",
}

export default async function GuidesPage() {
  const guides = await getAllGuides()
  const grouped = groupGuidesByCategory(guides)

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16">
          <div className="max-w-2xl mb-12">
            <h1 className="heading-2 text-text-primary mb-4">Guides</h1>
            <p className="body-text text-text-secondary">
              Everything you need to understand how Margin Invest works and how
              to get the most from it.
            </p>
          </div>

          <GuideCategoryTabs grouped={grouped} />
        </div>
      </div>
    </main>
  )
}
