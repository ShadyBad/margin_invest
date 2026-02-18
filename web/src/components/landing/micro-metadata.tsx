interface MicroMetadataProps {
  text: string
  className?: string
}

export function MicroMetadata({ text, className = "" }: MicroMetadataProps) {
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-widest text-text-tertiary ${className}`}
    >
      {text}
    </span>
  )
}
