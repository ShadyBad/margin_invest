import type { Metadata } from "next"
import { notFound } from "next/navigation"
import Link from "next/link"
import { compileMDX } from "next-mdx-remote/rsc"
import { Navbar } from "@/components/nav/navbar"
import { GuideLayout } from "@/components/guides/guide-layout"
import { mdxComponents } from "@/components/guides/mdx-components"
import { extractTocHeadings, type GuideFrontmatter } from "@/lib/guides"
import { getGuideBySlug, getAllGuideSlugs } from "@/lib/guides.server"

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  const slugs = await getAllGuideSlugs()
  return slugs.map((slug) => ({ slug }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const guide = await getGuideBySlug(slug)
  if (!guide) return { title: "Guide Not Found | Margin Invest" }

  return {
    title: `${guide.frontmatter.title} | Margin Invest Guides`,
    description: guide.frontmatter.description,
  }
}

export default async function GuidePage({ params }: PageProps) {
  const { slug } = await params
  const guide = await getGuideBySlug(slug)

  if (!guide) notFound()

  const headings = extractTocHeadings(guide.source)

  const { content } = await compileMDX<GuideFrontmatter>({
    source: guide.source,
    components: mdxComponents,
    options: { parseFrontmatter: false },
  })

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="pt-28 pb-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-8">
            <Link
              href="/guides"
              className="text-[13px] text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; All Guides
            </Link>
          </div>

          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-10">
            <h1 className="heading-2 text-text-primary mb-3">
              {guide.frontmatter.title}
            </h1>
            <div className="flex items-center gap-3 text-[13px] text-text-tertiary">
              <span>{guide.frontmatter.readingTime} min read</span>
              <span>&middot;</span>
              <span>Updated {guide.frontmatter.updatedAt}</span>
            </div>
          </div>

          <GuideLayout headings={headings}>{content}</GuideLayout>
        </div>
      </div>
    </main>
  )
}
