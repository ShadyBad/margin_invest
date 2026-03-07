import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ProviderIcons } from "../provider-icons"

describe("ProviderIcons", () => {
  it("renders Google and GitHub provider icons", () => {
    render(<ProviderIcons linkedProviders={[]} />)
    expect(screen.getByText("Google")).toBeInTheDocument()
    expect(screen.getByText("GitHub")).toBeInTheDocument()
  })

  it("shows connected state for linked providers", () => {
    render(<ProviderIcons linkedProviders={["google"]} />)
    const googleIcon = screen.getByLabelText("Google \u2014 Connected")
    expect(googleIcon).toBeInTheDocument()
    expect(screen.getAllByText("Connected").length).toBeGreaterThanOrEqual(1)
  })

  it("shows not connected state for available unlinked providers", () => {
    render(<ProviderIcons linkedProviders={[]} />)
    const googleIcon = screen.getByLabelText("Google \u2014 Not connected")
    expect(googleIcon).toBeInTheDocument()
    const githubIcon = screen.getByLabelText("GitHub \u2014 Not connected")
    expect(githubIcon).toBeInTheDocument()
  })

  it("renders connect buttons for available providers", () => {
    const onConnect = vi.fn()
    render(<ProviderIcons linkedProviders={[]} onConnect={onConnect} />)
    expect(screen.getByLabelText("Connect Google account")).toBeInTheDocument()
    expect(screen.getByLabelText("Connect GitHub account")).toBeInTheDocument()
  })

  it("calls onConnect when connect button is clicked", async () => {
    const user = userEvent.setup()
    const onConnect = vi.fn()
    render(<ProviderIcons linkedProviders={[]} onConnect={onConnect} />)

    await user.click(screen.getByLabelText("Connect Google account"))
    expect(onConnect).toHaveBeenCalledWith("google")
  })

  it("renders disconnect button for connected providers", () => {
    const onDisconnect = vi.fn()
    render(
      <ProviderIcons linkedProviders={["google"]} onDisconnect={onDisconnect} />
    )
    expect(screen.getByLabelText("Disconnect Google account")).toBeInTheDocument()
  })

  it("calls onDisconnect when disconnect button is clicked", async () => {
    const user = userEvent.setup()
    const onDisconnect = vi.fn()
    render(
      <ProviderIcons linkedProviders={["google"]} onDisconnect={onDisconnect} />
    )

    await user.click(screen.getByLabelText("Disconnect Google account"))
    expect(onDisconnect).toHaveBeenCalledWith("google")
  })

  it("shows connecting state when connecting prop matches provider", () => {
    const onConnect = vi.fn()
    render(
      <ProviderIcons linkedProviders={[]} onConnect={onConnect} connecting="google" />
    )
    expect(screen.getByText("Connecting...")).toBeInTheDocument()
  })

  it("does not render connect/disconnect buttons when callbacks not provided", () => {
    render(<ProviderIcons linkedProviders={["google"]} />)
    // Connected provider without onDisconnect — no disconnect button
    expect(screen.queryByLabelText("Disconnect Google account")).not.toBeInTheDocument()
    // Available provider without onConnect — no connect button
    expect(screen.queryByLabelText("Connect GitHub account")).not.toBeInTheDocument()
  })

  it("renders multiple connected providers correctly", () => {
    render(<ProviderIcons linkedProviders={["google", "github"]} />)
    expect(screen.getByLabelText("Google \u2014 Connected")).toBeInTheDocument()
    expect(screen.getByLabelText("GitHub \u2014 Connected")).toBeInTheDocument()
  })

  it("only renders Google and GitHub providers", () => {
    render(<ProviderIcons linkedProviders={[]} />)
    expect(screen.queryByText("Apple")).not.toBeInTheDocument()
    expect(screen.queryByText("Amazon")).not.toBeInTheDocument()
    expect(screen.queryByText("Facebook")).not.toBeInTheDocument()
  })
})
