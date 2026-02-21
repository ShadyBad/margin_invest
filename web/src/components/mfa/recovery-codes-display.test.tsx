import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { RecoveryCodesDisplay } from "./recovery-codes-display"

const mockCodes = [
  "aaaa-bbbb",
  "cccc-dddd",
  "eeee-ffff",
  "gggg-hhhh",
  "iiii-jjjj",
  "kkkk-llll",
  "mmmm-nnnn",
  "oooo-pppp",
]

describe("RecoveryCodesDisplay", () => {
  let onContinue: ReturnType<typeof vi.fn>

  beforeEach(() => {
    onContinue = vi.fn()
  })

  it("renders heading and description", () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)
    expect(screen.getByText("Save your recovery codes")).toBeInTheDocument()
    expect(
      screen.getByText(/These codes can be used to sign in if you lose access/)
    ).toBeInTheDocument()
  })

  it("renders all 8 recovery codes", () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)
    const codeElements = screen.getAllByTestId("recovery-code")
    expect(codeElements).toHaveLength(8)
    expect(codeElements[0]).toHaveTextContent("aaaa-bbbb")
    expect(codeElements[7]).toHaveTextContent("oooo-pppp")
  })

  it("Continue button is disabled until checkbox is checked", () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)
    const continueBtn = screen.getByRole("button", { name: "Continue" })
    expect(continueBtn).toBeDisabled()
  })

  it("Continue button is enabled after checkbox is checked", async () => {
    const user = userEvent.setup()
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)

    const checkbox = screen.getByTestId("saved-checkbox")
    await user.click(checkbox)

    const continueBtn = screen.getByRole("button", { name: "Continue" })
    expect(continueBtn).toBeEnabled()
  })

  it("calls onContinue when Continue is clicked after checkbox", async () => {
    const user = userEvent.setup()
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)

    const checkbox = screen.getByTestId("saved-checkbox")
    await user.click(checkbox)

    const continueBtn = screen.getByRole("button", { name: "Continue" })
    await user.click(continueBtn)

    expect(onContinue).toHaveBeenCalledTimes(1)
  })

  it("copy button copies codes to clipboard", async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
      configurable: true,
    })

    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)

    const copyBtn = screen.getByRole("button", { name: "Copy to clipboard" })
    await user.click(copyBtn)

    expect(writeText).toHaveBeenCalledWith(mockCodes.join("\n"))
    expect(screen.getByRole("button", { name: "Copied!" })).toBeInTheDocument()
  })

  it("download button triggers file download", async () => {
    const user = userEvent.setup()
    const createObjectURL = vi.fn(() => "blob:mock-url")
    const revokeObjectURL = vi.fn()
    Object.assign(URL, { createObjectURL, revokeObjectURL })

    const clickSpy = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = originalCreateElement(tag)
      if (tag === "a") {
        vi.spyOn(el, "click").mockImplementation(clickSpy)
      }
      return el
    })

    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={onContinue} />)

    const downloadBtn = screen.getByRole("button", { name: "Download as .txt" })
    await user.click(downloadBtn)

    expect(createObjectURL).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url")

    vi.restoreAllMocks()
  })
})
