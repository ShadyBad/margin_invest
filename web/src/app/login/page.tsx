import { LoginButtons } from "./login-buttons"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">
          Sign in to Margin Invest
        </h1>
        <LoginButtons />
      </div>
    </div>
  )
}
