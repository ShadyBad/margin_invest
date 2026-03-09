import { useEffect } from "react"

interface UseKeyboardNavOptions {
  onCmdK?: () => void
  onEscape?: () => void
}

export function useKeyboardNav({ onCmdK, onEscape }: UseKeyboardNavOptions) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onCmdK?.()
      }
      if (e.key === "Escape") {
        onEscape?.()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [onCmdK, onEscape])
}
