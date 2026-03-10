import { useEffect, type RefObject } from "react"

export interface UseKeyboardNavOptions {
  searchInputRef?: RefObject<HTMLInputElement | null>
  onCmdK?: () => void
  onEscape?: () => void
}

export function useKeyboardNav({
  searchInputRef,
  onCmdK,
  onEscape,
}: UseKeyboardNavOptions) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        searchInputRef?.current?.focus()
        onCmdK?.()
      }
      if (e.key === "Escape") {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur()
        }
        onEscape?.()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [searchInputRef, onCmdK, onEscape])
}
