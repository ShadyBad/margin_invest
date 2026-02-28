import type { Metadata } from "next"
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"

export const metadata: Metadata = {
  title: "Score Your Portfolio | Margin Invest",
  description: "Enter your tickers and see composite scores in 60 seconds.",
}

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      <OnboardingFlow />
    </div>
  )
}
