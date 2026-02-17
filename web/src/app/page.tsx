import dynamic from "next/dynamic"
import { auth } from "@/lib/auth"
import { Navbar } from "@/components/nav/navbar"
import { DNAProvider } from "@/components/landing/dna-provider"
import { ChapterHero } from "@/components/landing/chapter-hero"
import { ChapterEngine } from "@/components/landing/chapter-engine"
import { ChapterProof } from "@/components/landing/chapter-proof"
import { ChapterPath } from "@/components/landing/chapter-path"
import { ChapterIndicator } from "@/components/landing/chapter-indicator"

const FluidShader = dynamic(
  () => import("@/components/landing/fluid-shader").then((m) => ({ default: m.FluidShader })),
  { ssr: false },
)

async function getDNA() {
  try {
    const session = await auth()
    if (!session) return null
    const res = await fetch(`${process.env.API_URL || "http://localhost:8000"}/api/v1/users/me/dna`, {
      headers: {
        "X-User-Id": String((session as any).userId || ""),
        "X-User-Email": (session as any).user?.email || "",
      },
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function Home() {
  const dna = await getDNA()

  return (
    <DNAProvider dna={dna}>
      <main>
        <FluidShader
          baseColor={dna?.base}
          midColor={dna?.mid}
          accentColor={dna?.accent}
          tempo={dna?.tempo}
          density={dna?.density}
        />
        <Navbar />
        <div className="relative z-10">
          <ChapterHero />
          <div className="h-[50vh]" /> {/* Chapter break */}
          <section id="engine">
            <ChapterEngine />
          </section>
          <div className="h-[50vh]" />
          <ChapterProof />
          <div className="h-[50vh]" />
          <ChapterPath />
        </div>
        <ChapterIndicator
          chapters={4}
          activeChapter={0}
          labels={["The Signal", "The Engine", "The Proof", "The Path"]}
        />
      </main>
    </DNAProvider>
  )
}
