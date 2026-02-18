import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}))

vi.mock("@/components/ui/avatar", () => ({
  Avatar: ({ name }: { name: string }) => <div data-testid="avatar">{name}</div>,
}))

import { useSession } from "next-auth/react"
const mockUseSession = vi.mocked(useSession)

import { ProfileSection } from "../profile-section"

function mockSession(overrides: Record<string, unknown> = {}) {
  const base = {
    user: {
      name: "Jane Doe",
      email: "jane@example.com",
      image: null,
    },
    authMethod: "credentials" as const,
    oauthProvider: null as string | null,
    avatarUrl: null as string | null,
    oauthAvatarUrl: null as string | null,
    expires: "2099-01-01",
    ...overrides,
  }
  mockUseSession.mockReturnValue({
    data: base,
    status: "authenticated",
    update: vi.fn(),
  } as ReturnType<typeof useSession>)
}

describe("ProfileSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders profile heading", () => {
    mockSession()
    render(<ProfileSection />)
    expect(screen.getByRole("heading", { name: /profile/i })).toBeInTheDocument()
  })

  it("shows user name and email from session", () => {
    mockSession()
    render(<ProfileSection />)
    // Name appears in both the Avatar mock and the profile info
    expect(screen.getAllByText("Jane Doe").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("jane@example.com")).toBeInTheDocument()
  })

  it('shows "Email & Password" badge for credentials users', () => {
    mockSession({ authMethod: "credentials", oauthProvider: null })
    render(<ProfileSection />)
    expect(screen.getByText("Email & Password")).toBeInTheDocument()
  })

  it('shows "Google" badge for Google OAuth users', () => {
    mockSession({ authMethod: "oauth", oauthProvider: "google" })
    render(<ProfileSection />)
    expect(screen.getByText("Google")).toBeInTheDocument()
  })

  it('shows "GitHub" badge for GitHub OAuth users', () => {
    mockSession({ authMethod: "oauth", oauthProvider: "github" })
    render(<ProfileSection />)
    expect(screen.getByText("GitHub")).toBeInTheDocument()
  })

  it('shows "Upload Avatar" button', () => {
    mockSession()
    render(<ProfileSection />)
    expect(screen.getByText("Upload Avatar")).toBeInTheDocument()
  })

  it('shows "Remove" button when avatarUrl is present', () => {
    mockSession({ avatarUrl: "https://example.com/avatar.jpg" })
    render(<ProfileSection />)
    expect(screen.getByText("Remove")).toBeInTheDocument()
  })

  it('does NOT show "Remove" button when no avatarUrl', () => {
    mockSession({ avatarUrl: null })
    render(<ProfileSection />)
    expect(screen.queryByText("Remove")).not.toBeInTheDocument()
  })

  it("shows loading text when session has no user", () => {
    mockUseSession.mockReturnValue({
      data: { expires: "2099-01-01" } as ReturnType<typeof useSession>["data"],
      status: "authenticated",
      update: vi.fn(),
    } as ReturnType<typeof useSession>)
    render(<ProfileSection />)
    expect(screen.getByText("Loading profile information...")).toBeInTheDocument()
  })
})
