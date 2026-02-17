interface CapabilityBlockProps {
  title: string
  description: string
  tinted?: boolean
}

export function CapabilityBlock({
  title,
  description,
  tinted,
}: CapabilityBlockProps) {
  return (
    <div className={`p-6 ${tinted ? "bg-bg-subtle" : ""}`}>
      <h3 className="font-display text-[28px] md:text-[32px] lg:text-[36px] font-normal text-text-primary leading-[1.05] tracking-[-0.04em]">
        {title}
      </h3>
      <p className="mt-3 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
        {description}
      </p>
    </div>
  )
}
