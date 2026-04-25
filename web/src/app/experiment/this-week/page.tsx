import { Metadata } from "next"
import { CheckoutButton, ExperimentTracker } from "./checkout-button"

export const metadata: Metadata = {
  title: "This Week's 10 Survivors — Margin Invest",
  description:
    "The 10 stocks that survived our forensic elimination pipeline this week. Deterministic scoring, no opinions.",
}

export default function ExperimentThisWeekPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string }>
}) {
  return <PageContent searchParams={searchParams} />
}

async function PageContent({
  searchParams,
}: {
  searchParams: Promise<{ success?: string }>
}) {
  const params = await searchParams
  const success = params.success === "1"

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black px-6 text-white">
      <div className="mx-auto max-w-xl text-center">
        <ExperimentTracker success={success} />
        {success ? <SuccessMessage /> : <OfferContent />}
      </div>
    </main>
  )
}

function SuccessMessage() {
  return (
    <>
      <h1 className="mb-6 text-4xl font-bold tracking-tight">Purchase complete.</h1>
      <p className="text-lg text-neutral-400">
        Check your email. Your survivor list will arrive within 24 hours of the next market close.
      </p>
    </>
  )
}

function OfferContent() {
  return (
    <>
      <p className="mb-4 text-sm font-medium uppercase tracking-widest text-neutral-500">
        Margin Invest
      </p>

      <h1 className="mb-6 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
        10 stocks survived.
        <br />
        4,900+ didn&apos;t.
      </h1>

      <p className="mb-8 text-lg leading-relaxed text-neutral-400">
        Every week, our deterministic elimination pipeline scores the entire US equity universe. No
        opinions. No predictions. Pure forensic accounting.
      </p>

      <ul className="mb-10 space-y-3 text-left text-neutral-300">
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">{"\u2713"}</span>
          <span>
            <strong>Deterministic process</strong> — same inputs, same outputs, every time
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">{"\u2713"}</span>
          <span>
            <strong>Tamper-evident track record</strong> — every pick hash-chained and published
            publicly
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">{"\u2713"}</span>
          <span>
            <strong>Plain-English forensic report</strong> — factor decomposition and risk context
            for each survivor
          </span>
        </li>
      </ul>

      <CheckoutButton />

      <p className="mt-6 text-xs text-neutral-600">
        One-time purchase. No subscription. No account required.
      </p>
    </>
  )
}
