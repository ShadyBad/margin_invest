import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { useKeyboardNav } from "../use-keyboard-nav"

describe("useKeyboardNav", () => {
  it("calls onCmdK when Cmd+K is pressed", () => {
    const onCmdK = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))
    expect(onCmdK).toHaveBeenCalledOnce()
  })

  it("calls onCmdK when Ctrl+K is pressed", () => {
    const onCmdK = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))
    expect(onCmdK).toHaveBeenCalledOnce()
  })

  it("calls onEscape when Escape is pressed", () => {
    const onEscape = vi.fn()
    renderHook(() => useKeyboardNav({ onEscape }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }))
    expect(onEscape).toHaveBeenCalledOnce()
  })

  it("does not call handlers for unrelated keys", () => {
    const onCmdK = vi.fn()
    const onEscape = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK, onEscape }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }))
    expect(onCmdK).not.toHaveBeenCalled()
    expect(onEscape).not.toHaveBeenCalled()
  })

  it("cleans up listener on unmount", () => {
    const onCmdK = vi.fn()
    const { unmount } = renderHook(() => useKeyboardNav({ onCmdK }))
    unmount()
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))
    expect(onCmdK).not.toHaveBeenCalled()
  })
})
