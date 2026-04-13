import type { Metadata } from "next";
import Script from "next/script";
import { Suspense } from "react";
import { Inter_Tight, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import { PostHogProvider } from "@/lib/posthog/provider";
import { PostHogPageview } from "@/lib/posthog/pageview";
import { PostHogIdentify } from "@/lib/posthog/identify";
import { ConditionalFooter } from "@/components/layout/conditional-footer";
import { MfaRequiredModal } from "@/components/modals/mfa-required-modal";
import { AnalysisDisclaimerModal } from "@/components/modals/analysis-disclaimer-modal";
import { Toaster } from "sonner";
import "./globals.css";

const interTight = Inter_Tight({
  variable: "--font-inter-tight",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: {
    default: "Margin Invest — Discipline. Engineered.",
    template: "%s | Margin Invest",
  },
  description:
    "Deterministic investment analysis — quantitative scoring without human bias. 3,000+ US equities filtered to the ones worth your capital.",
  metadataBase: new URL("https://www.margin-invest.com"),
  openGraph: {
    title: "Margin Invest — Discipline. Engineered.",
    description:
      "A deterministic capital allocation system that replaces narrative with structure. Scoring 3,000+ US equities daily.",
    url: "https://www.margin-invest.com",
    siteName: "Margin Invest",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Margin Invest — Discipline. Engineered.",
    description:
      "A deterministic capital allocation system. Scoring 3,000+ US equities daily with zero human discretion.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${interTight.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased text-text-primary`}
      >
        {process.env.NEXT_PUBLIC_TERMLY_WEBSITE_UUID && (
          <Script
            src={`https://app.termly.io/resource-blocker/${process.env.NEXT_PUBLIC_TERMLY_WEBSITE_UUID}?autoBlock=on`}
            strategy="beforeInteractive"
          />
        )}
        <ThemeProvider attribute="class" forcedTheme="dark">
          <SessionProvider>
            <PostHogProvider>
              <Suspense fallback={null}>
                <PostHogPageview />
              </Suspense>
              <PostHogIdentify />
              <div className="min-h-screen bg-bg-primary">
                {children}
                <ConditionalFooter />
                <MfaRequiredModal />
                <AnalysisDisclaimerModal />
                <Toaster
                  theme="dark"
                  position="bottom-right"
                  toastOptions={{
                    style: {
                      background: "var(--color-bg-elevated)",
                      border: "1px solid var(--color-border-subtle)",
                      color: "var(--color-text-primary)",
                    },
                  }}
                />
              </div>
            </PostHogProvider>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
