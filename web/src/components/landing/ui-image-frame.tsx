interface UIImageFrameProps {
  src: string
  alt: string
  rotation?: number
}

export function UIImageFrame({ src, alt, rotation }: UIImageFrameProps) {
  return (
    <div
      className="border border-border-subtle rounded-[6px] overflow-hidden"
      style={rotation !== undefined ? { transform: `rotate(${rotation}deg)` } : undefined}
    >
      <img src={src} alt={alt} className="w-full h-auto block" />
    </div>
  )
}
