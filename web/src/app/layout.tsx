import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { Providers } from "@/components/providers";
import { Scene } from "@/components/scene";
import { SideRail, TopBar } from "@/components/site-header";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-plex-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "OnceSealed", template: "%s · OnceSealed" },
  description:
    "Prototype verification and privacy layer for carbon credit retirements. IEEE ClimateChain Hackathon 2026.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <Providers>
          <div className="relative isolate min-h-screen">
            <Scene />
            <SideRail />
            <div className="pb-28 md:pb-0 md:pl-[104px]">
              <TopBar />
              {children}
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
