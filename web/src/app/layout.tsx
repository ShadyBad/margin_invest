import type { Metadata } from "next";
import { Inter_Tight, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SessionProvider } from "@/components/providers/session-provider";
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
        className={`${interTight.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased bg-bg-primary text-text-primary`}
      >
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <SessionProvider>
            {children}
            <ConditionalFooter />
            <MfaRequiredModal />
            <AnalysisDisclaimerModal />
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
