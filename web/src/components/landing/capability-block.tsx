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
      <h3 className="text-[24px] md:text-[28px] lg:text-[32px] font-semibold text-text-primary leading-tight">
        {title}
      </h3>
      <p className="mt-3 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
        {description}
      </p>
    </div>
  )
}
