"use client"

import { useState } from "react"

interface TickerInputProps {
  onSubmit: (tickers: string[]) => void
  loading?: boolean
}

export function TickerInput({ onSubmit, loading = false }: TickerInputProps) {
  const [value, setValue] = useState("")

  const parseTickers = (input: string): string[] =>
    input
      .split(/[,\s]+/)
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0)

  const tickers = parseTickers(value)

  const handleSubmit = () => {
    if (tickers.length > 0) {
      onSubmit(tickers)
    }
  }

  return (
    <div className="w-full max-w-[480px]">
      <label className="block text-[13px] text-text-secondary mb-2">
        What are you holding?
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="AAPL, MSFT, GOOGL"
        className="w-full text-[17px] bg-bg-elevated border border-border-primary rounded-[4px] px-4 py-3 text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSubmit()
        }}
        disabled={loading}
      />
      <p className="text-[12px] text-text-tertiary mt-2">
        Enter 1-5 tickers, separated by commas
      </p>
      <button
        onClick={handleSubmit}
        disabled={tickers.length === 0 || loading}
        className="mt-4 w-full bg-accent text-white font-semibold text-[15px] rounded-[4px] h-12 hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Scoring..." : "Score my positions"}
      </button>
    </div>
  )
}
