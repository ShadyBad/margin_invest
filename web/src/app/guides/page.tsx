import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"
import { GuidesContent } from "@/components/guides/guides-content"
import { groupGuidesByCategory } from "@/lib/guides"
import { getAllGuides } from "@/lib/guides.server"

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
          <PageHeader
            category="GUIDES"
            title="The methodology is open."
            description="Every filter, factor, and formula — documented. Search or browse by category."
          />

          <GuidesContent grouped={grouped} allGuides={guides} />
        </div>
      </div>
    </main>
  )
}
