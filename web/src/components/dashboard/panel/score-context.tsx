interface ScoreContextProps {
  universeRank?: string
  scoringFrequency?: string
  lastScored?: string
}

export function ScoreContext({ universeRank, scoringFrequency, lastScored }: ScoreContextProps) {
  return (
    <div className="flex items-center gap-4 h-10 px-6 text-[13px]" data-testid="score-context">
      {universeRank && <span className="text-[#1A7A5A]">{universeRank}</span>}
      {scoringFrequency && <span className="text-[#5C5955]">{scoringFrequency}</span>}
      {lastScored && (
        <span className="text-[#5C5955] flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#1A7A5A]" />
          {lastScored}
        </span>
      )}
    </div>
  )
}
