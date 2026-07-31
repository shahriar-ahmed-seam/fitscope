import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";

import { Footer } from "@/components/site/Footer";
import { Nav } from "@/components/site/Nav";

import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "FitScope — resume ↔ job description fit intelligence",
    template: "%s · FitScope",
  },
  description:
    "Match a resume against a job posting requirement by requirement. Every score cites the exact resume line behind it, with a separate ATS readiness check.",
  keywords: [
    "resume matcher",
    "ATS score",
    "job description analysis",
    "resume optimisation",
    "semantic search",
    "NLP",
  ],
  authors: [{ name: "Shahriar Ahmed Seam" }],
  openGraph: {
    title: "FitScope — resume ↔ job description fit intelligence",
    description:
      "Requirement-level evidence matching between a resume and a job posting, plus a rule-based ATS readiness score.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#070a0f",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans">
        <a
          href="#main"
          className="no-print sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-ink-950"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
