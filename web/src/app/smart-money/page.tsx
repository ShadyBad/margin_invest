"use client"

import { useState } from "react"
import { AppShell } from "@/components/layout"
import { ProGate } from "@/components/dashboard/pro-gate"
import { TabNav } from "@/components/smart-money/tab-nav"
import { FundTracker } from "@/components/smart-money/fund-tracker"
import { MarketSignals } from "@/components/smart-money/market-signals"
import { CloneLab } from "@/components/smart-money/clone-lab"

const TABS = [
  { id: "fund-tracker", label: "Fund Tracker" },
  { id: "market-signals", label: "Market Signals" },
  { id: "clone-lab", label: "Clone Lab" },
]

export default function SmartMoneyPage() {
  const [activeTab, setActiveTab] = useState("fund-tracker")

  return (
    <AppShell>
      <div data-testid="smart-money-page">
        <h1 className="text-2xl font-semibold text-text-primary mb-1">Smart Money</h1>
        <p className="text-sm text-text-tertiary mb-6">
          Track institutional 13F filings and fund positioning
        </p>
        <ProGate>
          <TabNav tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
          {activeTab === "fund-tracker" && <FundTracker />}
          {activeTab === "market-signals" && <MarketSignals />}
          {activeTab === "clone-lab" && <CloneLab />}
        </ProGate>
      </div>
    </AppShell>
  )
}
