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
  title: "Margin Invest",
  description:
    "Deterministic investment analysis — quantitative scoring without human bias",
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
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <SessionProvider>
            <PostHogProvider>
              <Suspense fallback={null}>
                <PostHogPageview />
              </Suspense>
              <PostHogIdentify />
              <div className="min-h-screen" style={{ backgroundColor: '#0A0F0D' }}>
                {children}
                <ConditionalFooter />
                <MfaRequiredModal />
                <AnalysisDisclaimerModal />
              </div>
            </PostHogProvider>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
