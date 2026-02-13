import { Hero, HowItWorks, Performance, CTA } from "@/components/landing"

export default function Home() {
  return (
    <div className="bg-bg-primary min-h-screen">
      <Hero />
      <HowItWorks />
      <Performance />
      <CTA />
    </div>
  )
}
