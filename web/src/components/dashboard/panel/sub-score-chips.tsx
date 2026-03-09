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
          className="text-xs font-mono text-text-secondary bg-surface-overlay rounded-md px-2 py-0.5"
        >
          {sub.label}: {Math.round(sub.value)}
        </span>
      ))}
    </div>
  )
}
