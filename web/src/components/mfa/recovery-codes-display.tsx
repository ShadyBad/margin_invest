"use client"

import { useState } from "react"

export interface RecoveryCodesDisplayProps {
  codes: string[]
  onContinue: () => void
}

export function RecoveryCodesDisplay({ codes, onContinue }: RecoveryCodesDisplayProps) {
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const text = codes.join("\n")
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const text = [
      "Margin Invest Recovery Codes",
      "============================",
      "",
      "These codes can be used to sign in if you lose access",
      "to your authenticator app. Each code can only be used once.",
      "",
      ...codes,
      "",
      `Generated: ${new Date().toISOString()}`,
    ].join("\n")

    const blob = new Blob([text], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "margin-invest-recovery-codes.txt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col items-center gap-6 w-full">
      <h2 className="text-2xl font-bold text-text-primary">Save your recovery codes</h2>
      <p className="text-text-tertiary text-sm text-center">
        These codes can be used to sign in if you lose access to your authenticator app. Each code
        can only be used once. Store them somewhere safe.
      </p>

      <div className="grid grid-cols-2 gap-2 w-full bg-bg-elevated border border-border-primary rounded-sm p-4">
        {codes.map((code, i) => (
          <span
            key={i}
            className="font-mono text-sm text-text-primary text-center py-1"
            data-testid="recovery-code"
          >
            {code}
          </span>
        ))}
      </div>

      <div className="flex gap-3 w-full">
        <button
          type="button"
          onClick={handleCopy}
          className="flex-1 px-4 py-3 rounded-sm bg-bg-elevated border border-border-primary text-text-primary hover:border-accent-warm transition-colors text-sm font-medium"
        >
          {copied ? "Copied!" : "Copy to clipboard"}
        </button>
        <button
          type="button"
          onClick={handleDownload}
          className="flex-1 px-4 py-3 rounded-sm bg-bg-elevated border border-border-primary text-text-primary hover:border-accent-warm transition-colors text-sm font-medium"
        >
          Download as .txt
        </button>
      </div>

      <label className="flex items-center gap-3 w-full cursor-pointer">
        <input
          type="checkbox"
          checked={saved}
          onChange={(e) => setSaved(e.target.checked)}
          className="w-4 h-4 accent-accent-warm"
          data-testid="saved-checkbox"
        />
        <span className="text-sm text-text-tertiary">
          I&apos;ve saved these codes in a safe place
        </span>
      </label>

      <button
        type="button"
        onClick={onContinue}
        disabled={!saved}
        className="w-full px-4 py-3 rounded-sm bg-accent-warm text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Continue
      </button>
    </div>
  )
}
