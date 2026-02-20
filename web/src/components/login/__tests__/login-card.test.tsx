import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginCard } from "../login-card"

const { mockSignIn } = vi.hoisted(() => ({
  mockSignIn: vi.fn(),
}))

vi.mock("next-auth/react", () => ({
  signIn: mockSignIn,
}))

describe("LoginCard", () => {
  beforeEach(() => {
    mockSignIn.mockClear()
  })

  describe("structure", () => {
    it("renders the heading", () => {
      render(<LoginCard />)
      expect(screen.getByRole("heading", { name: /sign in to margin invest/i })).toBeInTheDocument()
    })

    it("renders the security subtext", () => {
      render(<LoginCard />)
      expect(screen.getByText(/secure login with bank-grade encryption/i)).toBeInTheDocument()
    })

    it("does not render the old register link (replaced by segmented control)", () => {
      render(<LoginCard />)
      expect(screen.queryByRole("link", { name: /create one/i })).not.toBeInTheDocument()
    })
  })

  describe("OAuth icons", () => {
    it("renders Google, Apple, and GitHub buttons", () => {
      render(<LoginCard />)
      expect(screen.getByLabelText("Sign in with Google")).toBeInTheDocument()
      expect(screen.getByLabelText(/sign in with apple/i)).toBeInTheDocument()
      expect(screen.getByLabelText("Sign in with GitHub")).toBeInTheDocument()
    })

    it("calls signIn with google on Google click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with Google"))
      expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/dashboard" })
    })

    it("calls signIn with github on GitHub click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with GitHub"))
      expect(mockSignIn).toHaveBeenCalledWith("github", { callbackUrl: "/dashboard" })
    })

    it("Apple button is disabled", () => {
      render(<LoginCard />)
      const appleBtn = screen.getByLabelText(/sign in with apple/i)
      expect(appleBtn).toBeDisabled()
      expect(appleBtn).toHaveAttribute("aria-disabled", "true")
    })

    it("Apple button does not call signIn", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText(/sign in with apple/i))
      expect(mockSignIn).not.toHaveBeenCalled()
    })
  })

  describe("credentials form", () => {
    it("shows 'Continue with email' toggle by default", () => {
      render(<LoginCard />)
      expect(screen.getByText("Continue with email")).toBeInTheDocument()
    })

    it("shows credentials form when 'Continue with email' is clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      expect(screen.getByLabelText("Email")).toBeInTheDocument()
      expect(screen.getByLabelText("Password", { selector: "input" })).toBeInTheDocument()
    })

    it("toggles text to 'Back to social login' when expanded", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      expect(screen.getByText("Back to social login")).toBeInTheDocument()
    })

    it("submits credentials with signIn", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      await user.type(screen.getByLabelText("Email"), "testuser")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "testpass123")
      // Find the form submit button (type="submit"), not the segmented control tab
      const allSignInButtons = screen.getAllByRole("button", { name: /^sign in$/i })
      const formSubmitButton = allSignInButtons.find(btn => btn.getAttribute("type") === "submit")!
      await user.click(formSubmitButton)
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        username: "testuser",
        password: "testpass123",
        callbackUrl: "/dashboard",
      })
    })

    it("toggles password visibility", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      const passwordInput = screen.getByLabelText("Password", { selector: "input" })
      expect(passwordInput).toHaveAttribute("type", "password")
      await user.click(screen.getByLabelText("Show password"))
      expect(passwordInput).toHaveAttribute("type", "text")
      await user.click(screen.getByLabelText("Hide password"))
      expect(passwordInput).toHaveAttribute("type", "password")
    })
  })

  describe("segmented control", () => {
    it("renders Sign In and Sign Up tabs", () => {
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      expect(within(segmented).getByRole("button", { name: "Sign In" })).toBeInTheDocument()
      expect(within(segmented).getByRole("button", { name: "Sign Up" })).toBeInTheDocument()
    })

    it("defaults to Sign In mode", () => {
      render(<LoginCard />)
      expect(
        screen.getByRole("heading", { name: /sign in to margin invest/i })
      ).toBeInTheDocument()
    })

    it("switches to Sign Up mode when Sign Up tab clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      expect(
        screen.getByRole("heading", { name: /create your account/i })
      ).toBeInTheDocument()
    })

    it("switches back to Sign In mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(within(segmented).getByRole("button", { name: "Sign In" }))
      expect(
        screen.getByRole("heading", { name: /sign in to margin invest/i })
      ).toBeInTheDocument()
    })
  })
})
