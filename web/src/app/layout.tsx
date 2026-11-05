import type { Metadata } from "next";
import { IBM_Plex_Sans_Arabic, Inter } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const plexArabic = IBM_Plex_Sans_Arabic({
  subsets: ["arabic"], weight: ["400", "500", "600", "700"], variable: "--font-arabic", display: "swap",
});

export const metadata: Metadata = {
  title: "Lumora Support Desk",
  description: "AI-assisted support ticket resolution with human review",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Language and theme come from cookies so the server renders the right `dir` and
  // colors on the first paint: no flash of LTR/light content for Arabic/dark users.
  const jar = await cookies();
  const lang = jar.get("lang")?.value === "ar" ? "ar" : "en";
  const theme = jar.get("theme")?.value === "dark" ? "dark" : "light";
  return (
    <html lang={lang} dir={lang === "ar" ? "rtl" : "ltr"} className={`${inter.variable} ${plexArabic.variable} ${theme === "dark" ? "dark" : ""}`}>
      <body className="font-sans">
        <Providers lang={lang} theme={theme}>{children}</Providers>
      </body>
    </html>
  );
}
