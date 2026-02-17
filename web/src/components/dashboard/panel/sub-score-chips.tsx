interface SubScore {
  label: string
  value: number
}

interface SubScoreChipsProps {
  subScores: SubScore[]
}

export function SubScoreChips({ subScores }: SubScoreChipsProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {subScores.map((sub) => (
        <span
          key={sub.label}
          className="text-[11px] font-mono text-[#9A9590] bg-white/[0.04] rounded-md px-2 py-0.5"
        >
          {sub.label}: {Math.round(sub.value)}
        </span>
      ))}
    </div>
  )
}
